use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub start_with_windows: bool,
    pub minimize_to_tray: bool,
    pub auto_start_monitoring: bool,
    pub update_interval: u64,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            start_with_windows: false,
            minimize_to_tray: true,
            auto_start_monitoring: false,
            update_interval: 2,
        }
    }
}

impl AppSettings {
    pub fn load(path: &Path) -> Self {
        match fs::read_to_string(path) {
            Ok(content) => serde_json::from_str::<AppSettings>(&content).unwrap_or_default(),
            Err(_) => AppSettings::default(),
        }
    }

    pub fn save(&self, path: &Path) -> anyhow::Result<()> {
        let serialized = serde_json::to_string_pretty(self)?;
        fs::write(path, serialized)?;
        Ok(())
    }
}
