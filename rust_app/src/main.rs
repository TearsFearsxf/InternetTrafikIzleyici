#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]

mod db;
mod monitor;
mod network_tools;
mod paths;
mod settings;
mod startup;

use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fs;
use std::sync::atomic::Ordering;
use std::sync::mpsc::{self, Receiver};
use std::thread;
use std::time::{Duration, Instant};

use anyhow::Context;
use chrono::{DateTime, Local};
use csv::Writer;
use eframe::egui::{self, Color32, RichText};
use eframe::{App, NativeOptions};
use egui_plot::{Bar, BarChart, Legend, Line, Plot, PlotPoints};
use rusqlite::Connection;
use settings::AppSettings;
use sysinfo::{Pid, System};
#[cfg(target_os = "windows")]
use tray_icon::menu::{Menu, MenuEvent, MenuId, MenuItem};
#[cfg(target_os = "windows")]
use tray_icon::{Icon, TrayIcon, TrayIconBuilder};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TrackingMode {
    General,
    App,
}

impl App for InternetTrafficApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.process_tray_events(ctx);
        self.handle_close_request(ctx);
        self.process_monitor_samples();
        self.process_async_results();
        self.update_resource_usage();
        self.draw_mini_widget(ctx);

        egui::TopBottomPanel::bottom("status_bar").show(ctx, |ui| {
            ui.horizontal_wrapped(|ui| {
                ui.label(format!("Durum: {}", self.status_text));
                ui.separator();
                ui.label(format!("RAM: {:.1} MB", self.resource_ram_mb));
                ui.separator();
                ui.label(format!("CPU: {:.1}%", self.resource_cpu_pct));
            });
        });

        egui::SidePanel::left("left_panel")
            .default_width(330.0)
            .resizable(false)
            .show(ctx, |ui| {
                ui.heading("Internet Trafik Izleyici (Rust)");
                ui.separator();

                ui.label("Takip Modu");
                ui.horizontal(|ui| {
                    ui.selectable_value(&mut self.tracking_mode, TrackingMode::General, "Genel");
                    ui.selectable_value(&mut self.tracking_mode, TrackingMode::App, "Uygulama");
                });

                if self.tracking_mode == TrackingMode::App {
                    ui.horizontal(|ui| {
                        egui::ComboBox::from_id_salt("app_combo")
                            .selected_text(if self.selected_app_name.is_empty() {
                                "Uygulama sec".to_string()
                            } else {
                                self.selected_app_name.clone()
                            })
                            .width(210.0)
                            .show_ui(ui, |ui| {
                                for app_name in &self.app_names {
                                    ui.selectable_value(
                                        &mut self.selected_app_name,
                                        app_name.clone(),
                                        app_name,
                                    );
                                }
                            });
                        if ui.button("Yenile").clicked() {
                            self.refresh_app_list();
                        }
                    });

                    ui.horizontal(|ui| {
                        ui.label("Elle gir:");
                        ui.text_edit_singleline(&mut self.process_name);
                    });

                    if self.is_monitoring {
                        let text = if self.app_mode_process_found {
                            "Uygulama processi bulundu"
                        } else {
                            "Uygulama processi bulunamadi"
                        };
                        let color = if self.app_mode_process_found {
                            Color32::from_rgb(80, 200, 120)
                        } else {
                            Color32::from_rgb(255, 120, 120)
                        };
                        ui.colored_label(color, text);
                    }
                }

                ui.separator();
                ui.horizontal(|ui| {
                    if ui
                        .add_enabled(!self.is_monitoring, egui::Button::new("BASLAT"))
                        .clicked()
                    {
                        self.start_monitoring();
                    }
                    if ui
                        .add_enabled(self.is_monitoring, egui::Button::new("DURDUR"))
                        .clicked()
                    {
                        self.stop_monitoring();
                    }
                });

                ui.separator();
                ui.collapsing("Kota Ayarlari", |ui| {
                    ui.checkbox(&mut self.limit_enabled, "Kota uyarisini aktif et");
                    ui.checkbox(&mut self.stop_on_limit, "Limit dolunca durdur");
                    ui.add(
                        egui::Slider::new(&mut self.data_limit_mb, 10.0..=50_000.0)
                            .text("Limit (MB)"),
                    );
                });

                ui.separator();
                ui.label("Zeka Ozellikleri");
                if ui
                    .add_enabled(
                        !self.speed_test_running,
                        egui::Button::new("Hizimi Test Et"),
                    )
                    .clicked()
                {
                    self.start_speed_test();
                }
                if ui
                    .add_enabled(!self.ip_analysis_running, egui::Button::new("IP Analizi"))
                    .clicked()
                {
                    self.start_ip_analysis();
                }
                if ui
                    .button(if self.mini_widget_visible {
                        "Mini Widget Kapat"
                    } else {
                        "Mini Widget Ac"
                    })
                    .clicked()
                {
                    self.mini_widget_visible = !self.mini_widget_visible;
                }
                if ui.button("Sisteme Sabitle").clicked() {
                    if let Err(err) = self.ensure_tray() {
                        self.status_text = format!("Sistem tepsisi hatasi: {err}");
                    }
                }
                if ui.button("Ayarlar").clicked() {
                    self.show_settings = true;
                }

                ui.separator();
                ui.label("Analiz ve Disa Aktarma");
                if ui.button("Grafikleri Guncelle").clicked() {
                    self.refresh_cache();
                }
                if ui.button("Istatistikleri Goster").clicked() {
                    self.show_stats = true;
                    self.refresh_cache();
                }
                if ui.button("CSV Olarak Disa Aktar").clicked() {
                    self.export_csv();
                }
                if ui.button("Veritabanini Temizle").clicked() {
                    self.confirm_clear_db = true;
                }
            });

        egui::CentralPanel::default().show(ctx, |ui| {
            let avg = self.average_speed_mbps();
            let speed_color = if avg > 20.0 {
                Color32::RED
            } else if avg > 10.0 {
                Color32::from_rgb(255, 166, 0)
            } else if avg > 2.0 {
                Color32::from_rgb(80, 200, 120)
            } else {
                Color32::LIGHT_GRAY
            };
            let speed_text = if avg < 0.1 {
                format!("{:.1} Kbps", avg * 1000.0)
            } else {
                format!("{avg:.2} Mbps")
            };

            ui.columns(4, |columns| {
                Self::draw_indicator_card(
                    &mut columns[0],
                    "Gecen Sure",
                    self.elapsed_text(),
                    Color32::from_rgb(220, 220, 220),
                );
                Self::draw_indicator_card(
                    &mut columns[1],
                    "Download",
                    Self::format_data_value(self.total_download_mb),
                    Color32::from_rgb(90, 160, 255),
                );
                Self::draw_indicator_card(
                    &mut columns[2],
                    "Upload",
                    Self::format_data_value(self.total_upload_mb),
                    Color32::from_rgb(255, 110, 110),
                );
                Self::draw_indicator_card(&mut columns[3], "Anlik Hiz", speed_text, speed_color);
            });

            ui.separator();
            self.draw_graph_tabs(ui);
        });

        if self.show_settings {
            egui::Window::new("Ayarlar")
                .open(&mut self.show_settings)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.checkbox(&mut self.settings.start_with_windows, "Windows ile baslat");
                    ui.checkbox(
                        &mut self.settings.auto_start_monitoring,
                        "Acilista izlemeyi baslat",
                    );
                    ui.checkbox(
                        &mut self.settings.minimize_to_tray,
                        "Kapatirken sistem tepsisine kucult",
                    );
                    ui.add(
                        egui::Slider::new(&mut self.settings.update_interval, 1..=10)
                            .text("Guncelleme araligi (sn)"),
                    );

                    let db_size_mb = fs::metadata(paths::db_path())
                        .map(|m| m.len() as f64 / (1024.0 * 1024.0))
                        .unwrap_or_default();
                    let session_count = db::session_count(&self.conn).unwrap_or_default();
                    ui.separator();
                    ui.label(format!("Veritabani boyutu: {:.2} MB", db_size_mb));
                    ui.label(format!("Toplam oturum: {session_count}"));
                    ui.label(format!("Veri klasoru: {}", paths::app_data_dir().display()));

                    if ui.button("Veri klasorunu ac").clicked() {
                        if let Err(err) = open::that(paths::app_data_dir()) {
                            self.status_text = format!("Klasor acilamadi: {err}");
                        }
                    }
                    if ui.button("Ayarlari Kaydet").clicked() {
                        if let Err(err) = self.settings.save(&self.settings_path) {
                            self.status_text = format!("Ayarlar kaydedilemedi: {err}");
                        } else if let Err(err) =
                            startup::set_startup(self.settings.start_with_windows)
                        {
                            self.status_text = format!("Startup ayari guncellenemedi: {err}");
                        } else {
                            self.status_text = "Ayarlar kaydedildi".to_string();
                        }
                    }
                });
        }

        if self.show_stats {
            egui::Window::new("Istatistikler")
                .open(&mut self.show_stats)
                .resizable(false)
                .show(ctx, |ui| {
                    if let Some(stats) = &self.stats_cache {
                        let hours = (stats.total_time_seconds / 3600.0).floor();
                        let minutes = ((stats.total_time_seconds % 3600.0) / 60.0).floor();
                        ui.label(format!("Toplam Oturum: {}", stats.total_sessions));
                        ui.label(format!(
                            "Toplam Sure: {:.0} saat {:.0} dakika",
                            hours, minutes
                        ));
                        ui.label(format!(
                            "Toplam Download: {:.2} MB",
                            stats.total_download_mb
                        ));
                        ui.label(format!("Toplam Upload: {:.2} MB", stats.total_upload_mb));
                        ui.label(format!(
                            "Ort. Download/Oturum: {:.2} MB",
                            stats.avg_download_mb
                        ));
                        ui.label(format!("Ort. Upload/Oturum: {:.2} MB", stats.avg_upload_mb));
                    } else {
                        ui.label("Henuz veri yok.");
                    }
                });
        }

        if self.confirm_clear_db {
            egui::Window::new("Onay")
                .collapsible(false)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.label("Tum sessions verileri silinecek. Emin misin?");
                    ui.horizontal(|ui| {
                        if ui.button("Evet").clicked() {
                            if let Err(err) = db::clear_sessions(&self.conn) {
                                self.status_text = format!("Veritabani temizlenemedi: {err}");
                            } else {
                                self.status_text = "Veritabani temizlendi".to_string();
                                self.refresh_cache();
                            }
                            self.confirm_clear_db = false;
                        }
                        if ui.button("Hayir").clicked() {
                            self.confirm_clear_db = false;
                        }
                    });
                });
        }

        if let Some(msg) = &self.speed_test_result_text {
            let mut open = true;
            let mut close_clicked = false;
            egui::Window::new("Hiz Testi Sonucu")
                .open(&mut open)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.label(msg);
                    if ui.button("Kapat").clicked() {
                        close_clicked = true;
                    }
                });
            if !open || close_clicked {
                self.speed_test_result_text = None;
            }
        }

        if let Some(msg) = &self.ip_analysis_text {
            let mut open = true;
            let mut close_clicked = false;
            egui::Window::new("IP Analizi")
                .open(&mut open)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.label(msg);
                    if ui.button("Kapat").clicked() {
                        close_clicked = true;
                    }
                });
            if !open || close_clicked {
                self.ip_analysis_text = None;
            }
        }

        ctx.request_repaint_after(Duration::from_millis(250));
    }
}

impl Drop for InternetTrafficApp {
    fn drop(&mut self) {
        if self.is_monitoring {
            self.stop_monitoring();
        }
    }
}

fn sector_points(
    center: egui::Pos2,
    radius: f32,
    start: f32,
    end: f32,
    segments: usize,
) -> Vec<egui::Pos2> {
    let mut points = Vec::with_capacity(segments + 2);
    points.push(center);
    for i in 0..=segments {
        let t = i as f32 / segments as f32;
        let a = start + (end - start) * t;
        let x = center.x + radius * a.cos();
        let y = center.y + radius * a.sin();
        points.push(egui::pos2(x, y));
    }
    points
}

#[cfg(target_os = "windows")]
fn create_tray_icon() -> Icon {
    let mut rgba = Vec::with_capacity(32 * 32 * 4);
    for y in 0..32 {
        for x in 0..32 {
            let in_bar = (y > 7 && y < 12) || (y > 14 && y < 19) || (y > 21 && y < 26);
            let (r, g, b) = if in_bar && x > 6 && x < 26 {
                (255, 255, 255)
            } else {
                (0, 120, 212)
            };
            rgba.extend_from_slice(&[r, g, b, 255]);
        }
    }
    Icon::from_rgba(rgba, 32, 32).unwrap_or_else(|_| {
        let fallback = vec![0_u8, 120, 212, 255];
        Icon::from_rgba(fallback, 1, 1).expect("fallback icon")
    })
}

fn main() {
    let app = match InternetTrafficApp::new() {
        Ok(app) => app,
        Err(err) => {
            eprintln!("Uygulama baslatilamadi: {err}");
            return;
        }
    };

    let native_options = NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("Internet Trafik Izleyici (Rust)")
            .with_inner_size([1280.0, 820.0])
            .with_min_inner_size([1024.0, 700.0]),
        ..Default::default()
    };

    let _ = eframe::run_native(
        "Internet Trafik Izleyici (Rust)",
        native_options,
        Box::new(|_cc| Ok(Box::new(app))),
    );
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum GraphTab {
    Line,
    Bar,
    Pie,
}

#[cfg(target_os = "windows")]
#[derive(Debug, Clone)]
struct TrayMenuIds {
    show: MenuId,
    widget: MenuId,
    speed: MenuId,
    quit: MenuId,
}

struct InternetTrafficApp {
    conn: Connection,
    settings_path: std::path::PathBuf,
    settings: AppSettings,

    tracking_mode: TrackingMode,
    process_name: String,
    selected_app_name: String,
    app_names: Vec<String>,
    app_mode_process_found: bool,
    last_app_probe: Instant,

    limit_enabled: bool,
    data_limit_mb: f64,
    stop_on_limit: bool,

    is_monitoring: bool,
    monitor_rx: Option<Receiver<monitor::TrafficSample>>,
    monitor_flag: Option<std::sync::Arc<std::sync::atomic::AtomicBool>>,
    start_wall: Option<DateTime<Local>>,
    start_instant: Option<Instant>,

    total_download_mb: f64,
    total_upload_mb: f64,
    speed_history: VecDeque<f64>,
    live_download_points: Vec<[f64; 2]>,
    live_upload_points: Vec<[f64; 2]>,

    sessions_cache: Vec<db::Session>,
    stats_cache: Option<db::Stats>,

    graph_tab: GraphTab,
    show_settings: bool,
    show_stats: bool,
    confirm_clear_db: bool,
    mini_widget_visible: bool,

    speed_test_running: bool,
    speed_test_rx: Option<Receiver<Result<network_tools::SpeedTestResult, String>>>,
    speed_test_result_text: Option<String>,

    ip_analysis_running: bool,
    ip_analysis_rx: Option<Receiver<Result<network_tools::IpAnalysis, String>>>,
    ip_analysis_text: Option<String>,

    status_text: String,
    system: System,
    last_resource_refresh: Instant,
    resource_ram_mb: f64,
    resource_cpu_pct: f32,

    #[cfg(target_os = "windows")]
    tray_icon: Option<TrayIcon>,
    #[cfg(target_os = "windows")]
    tray_menu_ids: Option<TrayMenuIds>,
    force_exit: bool,
}

impl InternetTrafficApp {
    fn new() -> anyhow::Result<Self> {
        let data_dir = paths::app_data_dir();
        fs::create_dir_all(&data_dir).with_context(|| {
            format!(
                "Uygulama veri klasoru olusturulamadi: {}",
                data_dir.display()
            )
        })?;

        let settings_path = paths::settings_path();
        let settings = AppSettings::load(&settings_path);

        let conn = db::open_connection(&paths::db_path())?;
        let sessions_cache = db::fetch_sessions(&conn).unwrap_or_default();
        let stats_cache = db::fetch_stats(&conn).unwrap_or(None);

        let mut app = Self {
            conn,
            settings_path,
            settings,
            tracking_mode: TrackingMode::General,
            process_name: String::new(),
            selected_app_name: String::new(),
            app_names: vec![],
            app_mode_process_found: false,
            last_app_probe: Instant::now() - Duration::from_secs(10),
            limit_enabled: false,
            data_limit_mb: 500.0,
            stop_on_limit: false,
            is_monitoring: false,
            monitor_rx: None,
            monitor_flag: None,
            start_wall: None,
            start_instant: None,
            total_download_mb: 0.0,
            total_upload_mb: 0.0,
            speed_history: VecDeque::with_capacity(5),
            live_download_points: Vec::new(),
            live_upload_points: Vec::new(),
            sessions_cache,
            stats_cache,
            graph_tab: GraphTab::Line,
            show_settings: false,
            show_stats: false,
            confirm_clear_db: false,
            mini_widget_visible: false,
            speed_test_running: false,
            speed_test_rx: None,
            speed_test_result_text: None,
            ip_analysis_running: false,
            ip_analysis_rx: None,
            ip_analysis_text: None,
            status_text: "Hazir".to_string(),
            system: System::new_all(),
            last_resource_refresh: Instant::now() - Duration::from_secs(5),
            resource_ram_mb: 0.0,
            resource_cpu_pct: 0.0,
            #[cfg(target_os = "windows")]
            tray_icon: None,
            #[cfg(target_os = "windows")]
            tray_menu_ids: None,
            force_exit: false,
        };

        app.refresh_app_list();
        if app.settings.auto_start_monitoring {
            app.start_monitoring();
        }
        Ok(app)
    }

    fn refresh_cache(&mut self) {
        self.sessions_cache = db::fetch_sessions(&self.conn).unwrap_or_default();
        self.stats_cache = db::fetch_stats(&self.conn).unwrap_or(None);
    }

    fn refresh_app_list(&mut self) {
        self.system.refresh_all();
        let mut names: BTreeSet<String> = BTreeSet::new();
        let common = [
            "chrome.exe",
            "firefox.exe",
            "msedge.exe",
            "opera.exe",
            "discord.exe",
            "steam.exe",
            "spotify.exe",
            "whatsapp.exe",
        ];
        for name in common {
            let _ = names.insert(name.to_string());
        }
        for proc_info in self.system.processes().values() {
            let name = proc_info.name().to_string().to_lowercase();
            if name.ends_with(".exe") {
                let _ = names.insert(name);
            }
        }
        self.app_names = names.into_iter().collect();
        if self.selected_app_name.is_empty() && !self.app_names.is_empty() {
            self.selected_app_name = self.app_names[0].clone();
        }
        self.status_text = format!("{} uygulama bulundu", self.app_names.len());
    }

    #[cfg(target_os = "windows")]
    fn ensure_tray(&mut self) -> anyhow::Result<()> {
        if self.tray_icon.is_some() {
            return Ok(());
        }

        let menu = Menu::new();
        let show_item = MenuItem::new("Uygulamayi Ac", true, None);
        let widget_item = MenuItem::new("Mini Widget", true, None);
        let speed_item = MenuItem::new("Hiz Testi", true, None);
        let quit_item = MenuItem::new("Cikis", true, None);
        menu.append(&show_item)?;
        menu.append(&widget_item)?;
        menu.append(&speed_item)?;
        menu.append(&quit_item)?;

        let icon = create_tray_icon();
        let tray_icon = TrayIconBuilder::new()
            .with_tooltip("Internet Trafik Izleyici")
            .with_menu(Box::new(menu))
            .with_icon(icon)
            .build()?;

        self.tray_menu_ids = Some(TrayMenuIds {
            show: show_item.id().clone(),
            widget: widget_item.id().clone(),
            speed: speed_item.id().clone(),
            quit: quit_item.id().clone(),
        });
        self.tray_icon = Some(tray_icon);
        self.status_text = "Uygulama sisteme sabitlendi".to_string();
        Ok(())
    }

    #[cfg(not(target_os = "windows"))]
    fn ensure_tray(&mut self) -> anyhow::Result<()> {
        Ok(())
    }

    fn process_tray_events(&mut self, ctx: &egui::Context) {
        #[cfg(target_os = "windows")]
        {
            if self.tray_icon.is_none() {
                return;
            }
            while let Ok(event) = MenuEvent::receiver().try_recv() {
                if let Some(ids) = &self.tray_menu_ids {
                    if event.id == ids.show {
                        ctx.send_viewport_cmd(egui::ViewportCommand::Minimized(false));
                        ctx.send_viewport_cmd(egui::ViewportCommand::Focus);
                    } else if event.id == ids.widget {
                        self.mini_widget_visible = !self.mini_widget_visible;
                    } else if event.id == ids.speed {
                        self.start_speed_test();
                    } else if event.id == ids.quit {
                        self.force_exit = true;
                        if self.is_monitoring {
                            self.stop_monitoring();
                        }
                        std::process::exit(0);
                    }
                }
            }
        }
    }

    fn handle_close_request(&mut self, ctx: &egui::Context) {
        if self.force_exit {
            if self.is_monitoring {
                self.stop_monitoring();
            }
            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            return;
        }

        let close_requested = ctx.input(|i| i.viewport().close_requested());
        if !close_requested {
            return;
        }

        if self.settings.minimize_to_tray {
            if let Err(err) = self.ensure_tray() {
                self.status_text = format!("Sistem tepsisi hatasi: {err}");
                return;
            }
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            ctx.send_viewport_cmd(egui::ViewportCommand::Minimized(true));
            self.status_text = "Uygulama arka planda calisiyor".to_string();
        } else if self.is_monitoring {
            self.stop_monitoring();
        }
    }

    fn start_monitoring(&mut self) {
        if self.is_monitoring {
            return;
        }

        if self.tracking_mode == TrackingMode::App {
            if self.process_name.trim().is_empty() && !self.selected_app_name.is_empty() {
                self.process_name = self.selected_app_name.clone();
            }
            if self.process_name.trim().is_empty() {
                self.status_text = "App modu icin process adi girmeniz lazim".to_string();
                return;
            }
        }

        let handle = monitor::start_monitor_thread(self.settings.update_interval.max(1));
        self.monitor_rx = Some(handle.rx);
        self.monitor_flag = Some(handle.running);

        self.is_monitoring = true;
        self.start_wall = Some(Local::now());
        self.start_instant = Some(Instant::now());
        self.total_download_mb = 0.0;
        self.total_upload_mb = 0.0;
        self.speed_history.clear();
        self.live_download_points.clear();
        self.live_upload_points.clear();

        if self.tracking_mode == TrackingMode::App {
            self.status_text = format!("Izleme basladi (uygulama: {})", self.process_name);
        } else {
            self.status_text = "Izleme basladi".to_string();
        }
    }

    fn stop_monitoring(&mut self) {
        if !self.is_monitoring {
            return;
        }

        if let Some(flag) = &self.monitor_flag {
            flag.store(false, Ordering::SeqCst);
        }

        self.is_monitoring = false;
        self.monitor_rx = None;
        self.monitor_flag = None;

        if let (Some(start_wall), Some(start_instant)) =
            (self.start_wall.take(), self.start_instant.take())
        {
            let end_wall = Local::now();
            let duration_seconds = start_instant.elapsed().as_secs_f64();
            let session = db::Session {
                start_time: start_wall.format("%Y-%m-%d %H:%M:%S").to_string(),
                end_time: end_wall.format("%Y-%m-%d %H:%M:%S").to_string(),
                duration_seconds,
                download_mb: self.total_download_mb,
                upload_mb: self.total_upload_mb,
                tracking_type: match self.tracking_mode {
                    TrackingMode::General => "general".to_string(),
                    TrackingMode::App => "app".to_string(),
                },
                process_name: if self.process_name.trim().is_empty() {
                    None
                } else {
                    Some(self.process_name.trim().to_string())
                },
            };

            if let Err(err) = db::insert_session(&self.conn, &session) {
                self.status_text = format!("Oturum kaydedilemedi: {err}");
            } else {
                self.status_text = "Izleme durdu ve oturum kaydedildi".to_string();
            }
            self.refresh_cache();
        }
    }

    fn probe_app_mode_process(&mut self) {
        if self.tracking_mode != TrackingMode::App || self.process_name.trim().is_empty() {
            return;
        }
        if self.last_app_probe.elapsed() < Duration::from_secs(3) {
            return;
        }
        self.last_app_probe = Instant::now();
        self.system.refresh_all();

        let target = self.process_name.trim().to_lowercase();
        self.app_mode_process_found = self
            .system
            .processes()
            .values()
            .any(|p| p.name().to_string().to_lowercase().contains(&target));
    }

    fn process_monitor_samples(&mut self) {
        let mut buffered = Vec::new();
        if let Some(rx) = &self.monitor_rx {
            while let Ok(sample) = rx.try_recv() {
                buffered.push(sample);
            }
        }

        let mut limit_triggered = false;
        for sample in buffered {
            self.total_download_mb += sample.download_mb;
            self.total_upload_mb += sample.upload_mb;

            self.speed_history.push_back(sample.speed_mbps);
            if self.speed_history.len() > 5 {
                let _ = self.speed_history.pop_front();
            }

            let elapsed_secs = self
                .start_instant
                .map(|s| s.elapsed().as_secs_f64())
                .unwrap_or_default();
            self.live_download_points
                .push([elapsed_secs, self.total_download_mb]);
            self.live_upload_points
                .push([elapsed_secs, self.total_upload_mb]);

            if self.limit_enabled
                && self.total_download_mb + self.total_upload_mb >= self.data_limit_mb
            {
                limit_triggered = true;
            }
        }

        self.probe_app_mode_process();
        if limit_triggered {
            self.status_text = format!(
                "Kota limiti doldu: {:.2} / {:.2} MB",
                self.total_download_mb + self.total_upload_mb,
                self.data_limit_mb
            );
            if self.stop_on_limit {
                self.stop_monitoring();
            }
        }
    }

    fn start_speed_test(&mut self) {
        if self.speed_test_running {
            return;
        }
        let (tx, rx) = mpsc::channel();
        self.speed_test_rx = Some(rx);
        self.speed_test_running = true;
        self.status_text = "Hiz testi basladi...".to_string();

        thread::spawn(move || {
            let result = network_tools::run_speed_test().map_err(|e| e.to_string());
            let _ = tx.send(result);
        });
    }

    fn start_ip_analysis(&mut self) {
        if self.ip_analysis_running {
            return;
        }
        let (tx, rx) = mpsc::channel();
        self.ip_analysis_rx = Some(rx);
        self.ip_analysis_running = true;
        self.status_text = "IP analizi basladi...".to_string();

        thread::spawn(move || {
            let result = network_tools::analyze_ip().map_err(|e| e.to_string());
            let _ = tx.send(result);
        });
    }

    fn process_async_results(&mut self) {
        if self.speed_test_running {
            let mut done = false;
            let mut msg = None;
            if let Some(rx) = &self.speed_test_rx {
                if let Ok(result) = rx.try_recv() {
                    done = true;
                    match result {
                        Ok(res) => {
                            let row = db::SpeedTestRow {
                                test_time: res.test_time.clone(),
                                download_mbps: res.download_mbps,
                                upload_mbps: res.upload_mbps,
                                ping_ms: res.ping_ms,
                            };
                            let _ = db::insert_speed_test(&self.conn, &row);
                            msg = Some(format!(
                                "HIZ TESTI\nTarih: {}\nDownload: {:.2} Mbps\nUpload: {:.2} Mbps (tahmini)\nPing: {:.1} ms",
                                res.test_time, res.download_mbps, res.upload_mbps, res.ping_ms
                            ));
                            self.status_text = "Hiz testi tamamlandi".to_string();
                        }
                        Err(err) => {
                            msg = Some(format!("Hiz testi basarisiz: {err}"));
                            self.status_text = "Hiz testi basarisiz".to_string();
                        }
                    }
                }
            }
            if done {
                self.speed_test_running = false;
                self.speed_test_rx = None;
                self.speed_test_result_text = msg;
            }
        }

        if self.ip_analysis_running {
            let mut done = false;
            let mut msg = None;
            if let Some(rx) = &self.ip_analysis_rx {
                if let Ok(result) = rx.try_recv() {
                    done = true;
                    match result {
                        Ok(res) => {
                            msg = Some(format!(
                                "IP ANALIZI\nPublic IP: {}\nLocal IP: {}",
                                res.public_ip, res.local_ip
                            ));
                            self.status_text = "IP analizi tamamlandi".to_string();
                        }
                        Err(err) => {
                            msg = Some(format!("IP analizi basarisiz: {err}"));
                            self.status_text = "IP analizi basarisiz".to_string();
                        }
                    }
                }
            }
            if done {
                self.ip_analysis_running = false;
                self.ip_analysis_rx = None;
                self.ip_analysis_text = msg;
            }
        }
    }

    fn average_speed_mbps(&self) -> f64 {
        if self.speed_history.is_empty() {
            return 0.0;
        }
        self.speed_history.iter().sum::<f64>() / self.speed_history.len() as f64
    }

    fn elapsed_text(&self) -> String {
        if let Some(start) = self.start_instant {
            let elapsed = start.elapsed().as_secs();
            let h = elapsed / 3600;
            let m = (elapsed % 3600) / 60;
            let s = elapsed % 60;
            format!("{h:02}:{m:02}:{s:02}")
        } else {
            "00:00:00".to_string()
        }
    }

    fn format_data_value(mb: f64) -> String {
        if mb >= 1024.0 {
            format!("{:.2} GB", mb / 1024.0)
        } else {
            format!("{:.2} MB", mb)
        }
    }

    fn export_csv(&mut self) {
        if let Some(path) = rfd::FileDialog::new()
            .set_file_name("internet_sessions.csv")
            .save_file()
        {
            let result = (|| -> anyhow::Result<()> {
                let sessions = db::fetch_sessions(&self.conn)?;
                let mut writer = Writer::from_path(&path)?;
                writer.write_record([
                    "start_time",
                    "end_time",
                    "duration_seconds",
                    "download_mb",
                    "upload_mb",
                    "tracking_type",
                    "process_name",
                ])?;
                for s in sessions {
                    writer.write_record([
                        s.start_time,
                        s.end_time,
                        format!("{:.2}", s.duration_seconds),
                        format!("{:.2}", s.download_mb),
                        format!("{:.2}", s.upload_mb),
                        s.tracking_type,
                        s.process_name.unwrap_or_default(),
                    ])?;
                }
                writer.flush()?;
                Ok(())
            })();

            self.status_text = match result {
                Ok(_) => format!("CSV kaydedildi: {}", path.display()),
                Err(err) => format!("CSV aktarim hatasi: {err}"),
            };
        }
    }

    fn update_resource_usage(&mut self) {
        if self.last_resource_refresh.elapsed() < Duration::from_secs(2) {
            return;
        }
        self.last_resource_refresh = Instant::now();
        self.system.refresh_all();
        if let Some(proc_info) = self.system.process(Pid::from_u32(std::process::id())) {
            self.resource_ram_mb = proc_info.memory() as f64 / (1024.0 * 1024.0);
            self.resource_cpu_pct = proc_info.cpu_usage();
        }
    }

    fn draw_indicator_card(ui: &mut egui::Ui, title: &str, value: String, color: Color32) {
        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.vertical_centered(|ui| {
                ui.label(title);
                ui.label(RichText::new(value).size(24.0).strong().color(color));
            });
        });
    }

    fn draw_graph_tabs(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.graph_tab, GraphTab::Line, "Cizgi Grafik");
            ui.selectable_value(&mut self.graph_tab, GraphTab::Bar, "Sutun Grafik");
            ui.selectable_value(&mut self.graph_tab, GraphTab::Pie, "Pasta Grafik");
        });
        ui.separator();

        match self.graph_tab {
            GraphTab::Line => {
                let down = Line::new(
                    "Download",
                    PlotPoints::from(self.live_download_points.clone()),
                )
                .color(Color32::from_rgb(90, 160, 255));
                let up = Line::new("Upload", PlotPoints::from(self.live_upload_points.clone()))
                    .color(Color32::from_rgb(255, 110, 110));
                Plot::new("live_line_plot")
                    .legend(Legend::default())
                    .height(300.0)
                    .show(ui, |plot_ui| {
                        plot_ui.line(down);
                        plot_ui.line(up);
                    });
            }
            GraphTab::Bar => {
                let mut daily = BTreeMap::<String, f64>::new();
                for s in &self.sessions_cache {
                    let date = s
                        .start_time
                        .split(' ')
                        .next()
                        .unwrap_or("unknown")
                        .to_string();
                    let total = s.download_mb + s.upload_mb;
                    *daily.entry(date).or_insert(0.0) += total;
                }
                let bars: Vec<Bar> = daily
                    .iter()
                    .enumerate()
                    .map(|(idx, (date, val))| {
                        Bar::new(idx as f64, *val).name(date.clone()).width(0.6)
                    })
                    .collect();
                Plot::new("daily_bar_plot")
                    .legend(Legend::default())
                    .height(300.0)
                    .show(ui, |plot_ui| {
                        plot_ui.bar_chart(
                            BarChart::new("Gunluk Toplam", bars)
                                .color(Color32::from_rgb(120, 190, 255)),
                        );
                    });
            }
            GraphTab::Pie => {
                let hist_download: f64 = self.sessions_cache.iter().map(|s| s.download_mb).sum();
                let hist_upload: f64 = self.sessions_cache.iter().map(|s| s.upload_mb).sum();
                self.draw_pie_chart(
                    ui,
                    hist_download + self.total_download_mb,
                    hist_upload + self.total_upload_mb,
                );
            }
        }
    }

    fn draw_pie_chart(&self, ui: &mut egui::Ui, download: f64, upload: f64) {
        let total = download + upload;
        let desired = egui::vec2(320.0, 320.0);
        let (rect, _) = ui.allocate_exact_size(desired, egui::Sense::hover());
        let painter = ui.painter_at(rect);
        if total <= f64::EPSILON {
            painter.text(
                rect.center(),
                egui::Align2::CENTER_CENTER,
                "Veri yok",
                egui::FontId::proportional(20.0),
                Color32::LIGHT_GRAY,
            );
            return;
        }

        let center = rect.center();
        let radius = rect.width().min(rect.height()) * 0.42;
        let start = -std::f32::consts::FRAC_PI_2;
        let down_angle =
            (std::f32::consts::TAU * (download / total) as f32).clamp(0.0, std::f32::consts::TAU);
        let mid = start + down_angle;
        let end = start + std::f32::consts::TAU;

        let down_points = sector_points(center, radius, start, mid, 64);
        let up_points = sector_points(center, radius, mid, end, 64);

        painter.add(egui::Shape::convex_polygon(
            down_points,
            Color32::from_rgb(90, 160, 255),
            egui::Stroke::NONE,
        ));
        painter.add(egui::Shape::convex_polygon(
            up_points,
            Color32::from_rgb(255, 110, 110),
            egui::Stroke::NONE,
        ));

        ui.add_space(8.0);
        ui.colored_label(
            Color32::from_rgb(90, 160, 255),
            format!(
                "Download: {:.2} MB ({:.1}%)",
                download,
                (download / total) * 100.0
            ),
        );
        ui.colored_label(
            Color32::from_rgb(255, 110, 110),
            format!(
                "Upload: {:.2} MB ({:.1}%)",
                upload,
                (upload / total) * 100.0
            ),
        );
    }

    fn draw_mini_widget(&mut self, ctx: &egui::Context) {
        if !self.mini_widget_visible {
            return;
        }

        let widget_id = egui::ViewportId::from_hash_of("mini_widget");
        let avg_speed = self.average_speed_mbps();
        let total_d = self.total_download_mb;
        let total_u = self.total_upload_mb;
        let mut should_close = false;

        ctx.show_viewport_immediate(
            widget_id,
            egui::ViewportBuilder::default()
                .with_title("Mini Trafik Widget")
                .with_inner_size([240.0, 125.0])
                .with_always_on_top()
                .with_resizable(false),
            |mini_ctx, _| {
                if mini_ctx.input(|i| i.viewport().close_requested()) {
                    should_close = true;
                    mini_ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
                }
                egui::CentralPanel::default().show(mini_ctx, |ui| {
                    ui.vertical_centered(|ui| {
                        let speed_text = if avg_speed < 0.1 {
                            format!("{:.1} Kbps", avg_speed * 1000.0)
                        } else {
                            format!("{avg_speed:.2} Mbps")
                        };
                        ui.label(RichText::new(speed_text).size(26.0).strong());
                        ui.label(format!("D: {:.2} MB | U: {:.2} MB", total_d, total_u));
                        if ui.button("Kapat").clicked() {
                            should_close = true;
                        }
                    });
                });
            },
        );

        if should_close {
            self.mini_widget_visible = false;
        }
    }
}
