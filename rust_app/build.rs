fn main() {
    #[cfg(target_os = "windows")]
    {
        let mut res = winres::WindowsResource::new();
        res.set_icon("..\\app_icon.ico");
        if let Err(err) = res.compile() {
            panic!("Windows icon resource compile failed: {err}");
        }
    }
}
