use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
    mpsc::{self, Receiver},
};
use std::thread;
use std::time::Duration;

use sysinfo::Networks;

#[derive(Debug, Clone)]
pub struct TrafficSample {
    pub download_mb: f64,
    pub upload_mb: f64,
    pub speed_mbps: f64,
}

pub struct MonitorHandle {
    pub running: Arc<AtomicBool>,
    pub rx: Receiver<TrafficSample>,
}

pub fn start_monitor_thread(interval_secs: u64) -> MonitorHandle {
    let (tx, rx) = mpsc::channel();
    let running = Arc::new(AtomicBool::new(true));
    let running_thread = Arc::clone(&running);

    thread::spawn(move || {
        let mut networks = Networks::new_with_refreshed_list();
        let (mut prev_recv, mut prev_sent) = snapshot_totals(&networks);

        while running_thread.load(Ordering::SeqCst) {
            thread::sleep(Duration::from_secs(interval_secs.max(1)));
            networks.refresh();

            let (curr_recv, curr_sent) = snapshot_totals(&networks);
            let recv_diff = curr_recv.saturating_sub(prev_recv);
            let sent_diff = curr_sent.saturating_sub(prev_sent);
            prev_recv = curr_recv;
            prev_sent = curr_sent;

            let download_mb = bytes_to_mb(recv_diff);
            let upload_mb = bytes_to_mb(sent_diff);
            let speed_mbps = ((recv_diff + sent_diff) as f64 * 8.0)
                / (interval_secs.max(1) as f64 * 1024.0 * 1024.0);

            if tx
                .send(TrafficSample {
                    download_mb,
                    upload_mb,
                    speed_mbps,
                })
                .is_err()
            {
                break;
            }
        }
    });

    MonitorHandle { running, rx }
}

fn snapshot_totals(networks: &Networks) -> (u64, u64) {
    networks
        .iter()
        .fold((0_u64, 0_u64), |(recv_acc, sent_acc), (_name, data)| {
            (
                recv_acc.saturating_add(data.total_received()),
                sent_acc.saturating_add(data.total_transmitted()),
            )
        })
}

fn bytes_to_mb(bytes: u64) -> f64 {
    bytes as f64 / (1024.0 * 1024.0)
}
