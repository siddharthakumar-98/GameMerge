use iso_extract::Iso;
use std::fs::{self, File};
use std::io::BufWriter;
use std::path::PathBuf;
use std::process::ExitCode;

const USAGE: &str = "usage:
  iso_extract list <image.iso>
  iso_extract extract <image.iso> <out_dir> [--only <substring>]...";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

fn run(args: &[String]) -> Result<(), String> {
    let (cmd, iso_path) = match args {
        [cmd, iso, ..] => (cmd.as_str(), iso),
        _ => return Err(USAGE.into()),
    };
    let file = File::open(iso_path).map_err(|e| format!("{iso_path}: {e}"))?;
    let mut iso = Iso::new(file);
    let entries = iso.entries().map_err(|e| e.to_string())?;

    match cmd {
        "list" => {
            for e in &entries {
                let kind = if e.is_dir { "dir " } else { "file" };
                println!("L{} {kind} {:>12} {}", e.layer, e.size, e.path);
            }
            let files = entries.iter().filter(|e| !e.is_dir);
            let (count, bytes) = files.fold((0, 0u64), |(n, b), e| (n + 1, b + e.size));
            println!("{count} files, {bytes} bytes");
        }
        "extract" => {
            let out = PathBuf::from(args.get(2).ok_or(USAGE)?);
            let mut only = Vec::new();
            let mut rest = args[3..].iter();
            while let Some(a) = rest.next() {
                match a.as_str() {
                    "--only" => only.push(rest.next().ok_or(USAGE)?.to_uppercase()),
                    _ => return Err(USAGE.into()),
                }
            }
            for e in entries.iter().filter(|e| !e.is_dir) {
                if !only.is_empty() && !only.iter().any(|o| e.path.to_uppercase().contains(o)) {
                    continue;
                }
                let dest = out.join(&e.path);
                if let Some(parent) = dest.parent() {
                    fs::create_dir_all(parent).map_err(|err| format!("{}: {err}", parent.display()))?;
                }
                let mut w = BufWriter::new(File::create(&dest).map_err(|err| format!("{}: {err}", dest.display()))?);
                let n = iso.copy_to(e, &mut w).map_err(|err| format!("{}: {err}", e.path))?;
                if n != e.size {
                    return Err(format!("{}: short read ({n} of {} bytes)", e.path, e.size));
                }
                println!("{:>12} {}", n, e.path);
            }
        }
        _ => return Err(USAGE.into()),
    }
    Ok(())
}
