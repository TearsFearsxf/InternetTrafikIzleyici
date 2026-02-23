use std::env;
use std::path::PathBuf;

pub fn app_data_dir() -> PathBuf {
    if let Ok(appdata) = env::var("APPDATA") {
        return PathBuf::from(appdata).join("InternetTrafikIzleyici");
    }

    env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("InternetTrafikIzleyici")
}

pub fn db_path() -> PathBuf {
    app_data_dir().join("internet_traffic.db")
}

pub fn settings_path() -> PathBuf {
    app_data_dir().join("settings.json")
}
