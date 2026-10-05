//! Minimal ISO9660 reader for PS2 DVD images, including dual-layer (DVD-9) discs.
//!
//! PS2 DVD-9 images are both layers concatenated. Layer 0 is a normal ISO9660
//! volume. Layer 1 carries its own primary volume descriptor at sector
//! `layer0_volume_space`, and its LBAs are relative to the layer break
//! (`layer0_volume_space - 16`). Generic tools only see layer 0.

use std::io::{self, Read, Seek, SeekFrom};

pub const SECTOR: u64 = 2048;

#[derive(Debug, Clone)]
pub struct Entry {
    /// Path with `/` separators and the `;1` version suffix stripped.
    pub path: String,
    pub layer: u8,
    /// Absolute byte offset in the image.
    pub offset: u64,
    pub size: u64,
    pub is_dir: bool,
}

struct Pvd {
    volume_space: u32,
    root_lba: u32,
    root_size: u32,
}

pub struct Iso<R> {
    r: R,
}

impl<R: Read + Seek> Iso<R> {
    pub fn new(r: R) -> Self {
        Iso { r }
    }

    fn read_at(&mut self, offset: u64, len: usize) -> io::Result<Vec<u8>> {
        let mut buf = vec![0u8; len];
        self.r.seek(SeekFrom::Start(offset))?;
        self.r.read_exact(&mut buf)?;
        Ok(buf)
    }

    fn pvd_at(&mut self, sector: u64) -> io::Result<Option<Pvd>> {
        let d = match self.read_at(sector * SECTOR, SECTOR as usize) {
            Ok(d) => d,
            Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => return Ok(None),
            Err(e) => return Err(e),
        };
        if d[0] != 1 || &d[1..6] != b"CD001" {
            return Ok(None);
        }
        let root = &d[156..190];
        Ok(Some(Pvd {
            volume_space: le32(&d, 80),
            root_lba: le32(root, 2),
            root_size: le32(root, 10),
        }))
    }

    /// Lists every file and directory on both layers.
    pub fn entries(&mut self) -> io::Result<Vec<Entry>> {
        let pvd0 = self
            .pvd_at(16)?
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "no ISO9660 volume descriptor"))?;
        let mut out = Vec::new();
        self.walk(0, 0, pvd0.root_lba, pvd0.root_size, "", &mut out)?;

        let l1_pvd_sector = pvd0.volume_space as u64;
        if let Some(pvd1) = self.pvd_at(l1_pvd_sector)? {
            let base = l1_pvd_sector - 16;
            self.walk(1, base, pvd1.root_lba, pvd1.root_size, "", &mut out)?;
        }
        Ok(out)
    }

    fn walk(&mut self, layer: u8, base: u64, lba: u32, size: u32, prefix: &str, out: &mut Vec<Entry>) -> io::Result<()> {
        let d = self.read_at((base + lba as u64) * SECTOR, size as usize)?;
        let mut i = 0usize;
        while i < d.len() {
            let len = d[i] as usize;
            if len == 0 {
                // Records never straddle sectors; zero padding means skip to the next one.
                i = (i / SECTOR as usize + 1) * SECTOR as usize;
                continue;
            }
            let rec = &d[i..i + len];
            let name_len = rec[32] as usize;
            let name = &rec[33..33 + name_len];
            if name != [0] && name != [1] {
                let name = String::from_utf8_lossy(name);
                let name = name.split(';').next().unwrap_or_default();
                let path = if prefix.is_empty() { name.to_string() } else { format!("{prefix}/{name}") };
                let (elba, esize) = (le32(rec, 2), le32(rec, 10));
                let is_dir = rec[25] & 2 != 0;
                out.push(Entry {
                    path: path.clone(),
                    layer,
                    offset: (base + elba as u64) * SECTOR,
                    size: esize as u64,
                    is_dir,
                });
                if is_dir {
                    self.walk(layer, base, elba, esize, &path, out)?;
                }
            }
            i += len;
        }
        Ok(())
    }

    /// Copies one entry's bytes into `w`.
    pub fn copy_to(&mut self, e: &Entry, w: &mut impl io::Write) -> io::Result<u64> {
        self.r.seek(SeekFrom::Start(e.offset))?;
        io::copy(&mut (&mut self.r).take(e.size), w)
    }
}

fn le32(d: &[u8], at: usize) -> u32 {
    u32::from_le_bytes(d[at..at + 4].try_into().unwrap())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    fn dir_record(lba: u32, size: u32, flags: u8, name: &[u8]) -> Vec<u8> {
        let len = 33 + name.len() + (name.len() + 1) % 2;
        let mut r = vec![0u8; len];
        r[0] = len as u8;
        r[2..6].copy_from_slice(&lba.to_le_bytes());
        r[10..14].copy_from_slice(&size.to_le_bytes());
        r[25] = flags;
        r[32] = name.len() as u8;
        r[33..33 + name.len()].copy_from_slice(name);
        r
    }

    fn put_volume(img: &mut [u8], pvd_sector: usize, base: usize, volume_space: u32, file: &[u8], name: &[u8]) {
        let pvd = &mut img[pvd_sector * 2048..];
        pvd[0] = 1;
        pvd[1..6].copy_from_slice(b"CD001");
        pvd[80..84].copy_from_slice(&volume_space.to_le_bytes());
        let root = dir_record(18, 2048, 2, &[0]);
        pvd[156..156 + root.len()].copy_from_slice(&root);

        let mut dir = Vec::new();
        dir.extend(dir_record(18, 2048, 2, &[0]));
        dir.extend(dir_record(18, 2048, 2, &[1]));
        dir.extend(dir_record(19, file.len() as u32, 0, name));
        img[(base + 18) * 2048..][..dir.len()].copy_from_slice(&dir);
        img[(base + 19) * 2048..][..file.len()].copy_from_slice(file);
    }

    #[test]
    fn reads_both_layers() {
        // Layer 0 has 24 sectors; layer 1 starts at the break (24 - 16 = 8).
        let mut img = vec![0u8; 48 * 2048];
        put_volume(&mut img, 16, 0, 24, b"layer zero", b"A.BIN;1");
        put_volume(&mut img, 24, 8, 40, b"layer one!", b"B.PSS;1");

        let mut iso = Iso::new(Cursor::new(img));
        let entries = iso.entries().unwrap();
        let names: Vec<_> = entries.iter().map(|e| (e.path.as_str(), e.layer)).collect();
        assert_eq!(names, [("A.BIN", 0), ("B.PSS", 1)]);

        let mut buf = Vec::new();
        iso.copy_to(&entries[1], &mut buf).unwrap();
        assert_eq!(buf, b"layer one!");
    }
}
