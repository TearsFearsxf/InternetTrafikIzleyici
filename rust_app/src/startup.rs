#[cfg(target_os = "windows")]
pub fn set_startup(enabled: bool) -> anyhow::Result<()> {
    use std::env;
    use winreg::RegKey;
    use winreg::enums::{HKEY_CURRENT_USER, KEY_SET_VALUE};

    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let run_key = hkcu.open_subkey_with_flags(
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        KEY_SET_VALUE,
    )?;

    if enabled {
        let exe = env::current_exe()?;
        run_key.set_value(
            "InternetTrafikIzleyiciRust",
            &exe.to_string_lossy().to_string(),
        )?;
    } else {
        let _ = run_key.delete_value("InternetTrafikIzleyiciRust");
    }

    Ok(())
}

#[cfg(not(target_os = "windows"))]
pub fn set_startup(_enabled: bool) -> anyhow::Result<()> {
    Ok(())
}
