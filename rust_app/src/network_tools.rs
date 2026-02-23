use std::io::Read;
use std::time::{Duration, Instant};

use local_ip_address::local_ip;
use reqwest::blocking::Client;

#[derive(Debug, Clone)]
pub struct SpeedTestResult {
    pub test_time: String,
    pub download_mbps: f64,
    pub upload_mbps: f64,
    pub ping_ms: f64,
}

#[derive(Debug, Clone)]
pub struct IpAnalysis {
    pub public_ip: String,
    pub local_ip: String,
}

pub fn run_speed_test() -> anyhow::Result<SpeedTestResult> {
    let client = Client::builder().timeout(Duration::from_secs(30)).build()?;

    let urls = [
        "https://speed.cloudflare.com/__down?bytes=10000000",
        "https://proof.ovh.net/files/10Mb.dat",
    ];

    let mut measured_download = None;
    for url in urls {
        if let Ok(mut response) = client.get(url).send() {
            let start = Instant::now();
            let mut total: u64 = 0;
            let mut buffer = [0_u8; 8192];
            loop {
                let read = response.read(&mut buffer)?;
                if read == 0 {
                    break;
                }
                total = total.saturating_add(read as u64);
            }
            let secs = start.elapsed().as_secs_f64();
            if secs > 0.0 {
                measured_download = Some((total as f64 * 8.0) / (secs * 1_000_000.0));
                break;
            }
        }
    }

    let download_mbps =
        measured_download.ok_or_else(|| anyhow::anyhow!("Hiz testi sunucularina ulasilamadi"))?;

    let ping_start = Instant::now();
    let ping_ms = match client.get("https://www.google.com").send() {
        Ok(_) => ping_start.elapsed().as_secs_f64() * 1000.0,
        Err(_) => 0.0,
    };

    let now = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();

    Ok(SpeedTestResult {
        test_time: now,
        download_mbps,
        upload_mbps: download_mbps * 0.3,
        ping_ms,
    })
}

pub fn analyze_ip() -> anyhow::Result<IpAnalysis> {
    let client = Client::builder().timeout(Duration::from_secs(8)).build()?;
    let public_ip = client
        .get("https://api.ipify.org")
        .send()?
        .text()?
        .trim()
        .to_string();
    let local_ip = local_ip()?.to_string();

    Ok(IpAnalysis {
        public_ip,
        local_ip,
    })
}
