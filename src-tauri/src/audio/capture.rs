use anyhow::Result;
use cpal::{
    traits::{DeviceTrait, StreamTrait},
    Device, Stream, StreamConfig,
};
use crossbeam_channel::Sender;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use tauri::Emitter;

/// Owns a cpal input stream; keeps it alive until dropped.
pub struct CaptureStream {
    _stream: Stream,
}

// SAFETY: cpal's Stream on Windows holds PhantomData<*mut ()> solely to
// opt out of auto-Send; actual access is serialised through AudioManager's Mutex.
unsafe impl Send for CaptureStream {}

impl CaptureStream {
    /// Standard microphone capture via cpal/WASAPI.
    pub fn new_mic(device: &Device, config: &StreamConfig, tx: Sender<Vec<f32>>) -> Result<Self> {
        let stream = device.build_input_stream(
            config,
            move |data: &[f32], _| {
                let _ = tx.try_send(data.to_vec());
            },
            |err| log::error!("mic capture error: {err}"),
            None,
        )?;
        stream.play()?;
        Ok(Self { _stream: stream })
    }
}

// ── WASAPI loopback (Windows only) ───────────────────────────────────────────

macro_rules! elog {
    ($app:expr, $($arg:tt)*) => {{
        let msg = format!($($arg)*);
        log::info!("{}", msg);
        let _ = $app.emit("engine-log", serde_json::json!({ "message": msg }));
    }};
}

macro_rules! eerr {
    ($app:expr, $($arg:tt)*) => {{
        let msg = format!($($arg)*);
        log::error!("{}", msg);
        let _ = $app.emit("engine-error", serde_json::json!({ "message": msg }));
    }};
}

#[cfg(target_os = "windows")]
pub fn loopback_capture_thread(
    device_name: String,
    tx:          Sender<Vec<f32>>,
    stop:        Arc<AtomicBool>,
    app:         tauri::AppHandle,
) -> Result<()> {
    use wasapi::{get_default_device, initialize_mta, DeviceCollection, Direction, SampleType, ShareMode};

    elog!(app, "Loopback: initialising COM MTA");
    initialize_mta().map_err(|e| anyhow::anyhow!("COM MTA init: {e}"))?;

    let device = if device_name.is_empty() {
        return Err(anyhow::anyhow!("no capture device set"));
    } else {
        elog!(app, "Loopback: looking for render device '{device_name}'");
        let collection = DeviceCollection::new(&Direction::Render)
            .map_err(|e| anyhow::anyhow!("DeviceCollection::new: {e}"))?;
        collection.get_device_with_name(&device_name)
            .unwrap_or_else(|_| {
                let def = get_default_device(&Direction::Render).expect("no default render device");
                let def_name = def.get_friendlyname().unwrap_or_else(|_| "unknown".into());
                let _ = app.emit("engine-error", serde_json::json!({
                    "message": format!("Render device '{device_name}' not found — fell back to '{def_name}'. Set the correct device on this channel.")
                }));
                def
            })
    };

    let dev_name = device.get_friendlyname().unwrap_or_else(|_| "unknown".into());
    elog!(app, "Loopback: render device = '{dev_name}'");

    let mut audio_client = device
        .get_iaudioclient()
        .map_err(|e| anyhow::anyhow!("IAudioClient: {e}"))?;

    let mix_fmt = audio_client
        .get_mixformat()
        .map_err(|e| anyhow::anyhow!("get_mixformat: {e}"))?;

    let native_channels  = mix_fmt.get_nchannels() as usize;
    let bytes_per_frame  = mix_fmt.get_blockalign() as usize;
    let bits_per_sample  = mix_fmt.get_bitspersample();
    let is_float         = matches!(mix_fmt.get_subformat(), Ok(SampleType::Float));

    elog!(app,
        "Loopback: mix format {}Hz ×{}ch {}bit {}",
        mix_fmt.get_samplespersec(), native_channels, bits_per_sample,
        if is_float { "float" } else { "int" }
    );

    let (_def_period, min_period) = audio_client
        .get_periods()
        .map_err(|e| anyhow::anyhow!("get periods: {e}"))?;

    elog!(app, "Loopback: calling initialize_client (convert=false, loopback)");
    audio_client
        .initialize_client(
            &mix_fmt,
            min_period as i64,
            &Direction::Capture,
            &ShareMode::Shared,
            false,
        )
        .map_err(|e| anyhow::anyhow!("initialize_client: {e}"))?;

    elog!(app, "Loopback: setting event handle");
    let h_event = audio_client
        .set_get_eventhandle()
        .map_err(|e| anyhow::anyhow!("set_get_eventhandle: {e}"))?;

    elog!(app, "Loopback: getting capture client");
    let capture_client = audio_client
        .get_audiocaptureclient()
        .map_err(|e| anyhow::anyhow!("get_audiocaptureclient: {e}"))?;

    elog!(app, "Loopback: starting stream");
    audio_client
        .start_stream()
        .map_err(|e| anyhow::anyhow!("start_stream: {e}"))?;

    elog!(app, "Loopback: capture loop running on '{dev_name}'");

    const TARGET_CH:    usize = 2;
    const CHUNK_FRAMES: usize = 480; // 10 ms @ 48 kHz

    let mut raw_buf: Vec<u8>  = vec![0u8; CHUNK_FRAMES * bytes_per_frame * 8];
    let mut queue:   Vec<f32> = Vec::with_capacity(CHUNK_FRAMES * TARGET_CH * 8);
    let mut frames_logged:    u64 = 0;

    while !stop.load(Ordering::SeqCst) {
        h_event.wait_for_event(100).ok();

        loop {
            let nbr_frames = match capture_client
                .get_next_nbr_frames()
                .map_err(|e| anyhow::anyhow!("get_next_nbr_frames: {e}"))?
            {
                Some(n) if n > 0 => n as usize,
                _ => break,
            };

            let needed = nbr_frames * bytes_per_frame;
            if raw_buf.len() < needed {
                raw_buf.resize(needed, 0u8);
            }

            let (frames_read, flags) = capture_client
                .read_from_device(bytes_per_frame, &mut raw_buf[..needed])
                .map_err(|e| anyhow::anyhow!("read_from_device: {e}"))?;

            if frames_read == 0 { break; }

            // Log first captured frame so user can see data is flowing.
            frames_logged += frames_read as u64;
            if frames_logged == frames_read as u64 || frames_logged % 48000 == 0 {
                elog!(app, "Loopback: captured {} frames so far (silent={})", frames_logged, flags.silent);
            }

            let n_raw_samples = frames_read as usize * native_channels;
            let silent = flags.silent;

            let native_f32: Vec<f32> = if silent {
                vec![0.0f32; n_raw_samples]
            } else if is_float && bits_per_sample == 32 {
                bytemuck::cast_slice::<u8, f32>(&raw_buf[..frames_read as usize * bytes_per_frame])
                    [..n_raw_samples]
                    .to_vec()
            } else if !is_float && bits_per_sample == 16 {
                raw_buf[..frames_read as usize * bytes_per_frame]
                    .chunks_exact(2)
                    .map(|b| i16::from_le_bytes([b[0], b[1]]) as f32 / 32768.0)
                    .collect()
            } else if !is_float && bits_per_sample == 24 {
                raw_buf[..frames_read as usize * bytes_per_frame]
                    .chunks_exact(3)
                    .map(|b| {
                        let v = i32::from_le_bytes([b[0], b[1], b[2], 0]) >> 8;
                        v as f32 / 8_388_608.0
                    })
                    .collect()
            } else if !is_float && bits_per_sample == 32 {
                bytemuck::cast_slice::<u8, i32>(&raw_buf[..frames_read as usize * bytes_per_frame])
                    [..n_raw_samples]
                    .iter()
                    .map(|&s| s as f32 / 2_147_483_648.0)
                    .collect()
            } else {
                eerr!(app, "Loopback: unhandled format {}bit {}", bits_per_sample,
                    if is_float { "float" } else { "int" });
                vec![0.0f32; n_raw_samples]
            };

            let stereo: Vec<f32> = if native_channels == TARGET_CH {
                native_f32
            } else if native_channels == 1 {
                native_f32.iter().flat_map(|&s| [s, s]).collect()
            } else {
                native_f32
                    .chunks_exact(native_channels)
                    .flat_map(|c| [c[0], c[1]])
                    .collect()
            };

            queue.extend_from_slice(&stereo);
        }

        while queue.len() >= CHUNK_FRAMES * TARGET_CH {
            let chunk: Vec<f32> = queue.drain(..CHUNK_FRAMES * TARGET_CH).collect();
            if tx.try_send(chunk).is_err() {
                if !stop.load(Ordering::SeqCst) {
                    eerr!(app, "Loopback: channel full or disconnected — stopping");
                }
                stop.store(true, Ordering::SeqCst);
                break;
            }
        }
    }

    audio_client.stop_stream().ok();
    elog!(app, "Loopback: stream stopped");
    Ok(())
}

#[cfg(not(target_os = "windows"))]
pub fn loopback_capture_thread(
    _device_name: String,
    _tx:          Sender<Vec<f32>>,
    _stop:        Arc<AtomicBool>,
    _app:         tauri::AppHandle,
) -> Result<()> {
    anyhow::bail!("WASAPI loopback is Windows-only")
}

// ── Mic / eCapture capture (Windows only) ────────────────────────────────────

#[cfg(target_os = "windows")]
pub fn mic_capture_thread(
    device_name: String,
    tx:          Sender<Vec<f32>>,
    stop:        Arc<AtomicBool>,
    app:         tauri::AppHandle,
) -> Result<()> {
    use wasapi::{get_default_device, initialize_mta, DeviceCollection, Direction, SampleType, ShareMode};

    elog!(app, "MicCapture: initialising COM MTA");
    initialize_mta().map_err(|e| anyhow::anyhow!("COM MTA init: {e}"))?;

    let device = if device_name.is_empty() {
        return Err(anyhow::anyhow!("no capture device set"));
    } else {
        elog!(app, "MicCapture: looking for capture device '{device_name}'");
        let collection = DeviceCollection::new(&Direction::Capture)
            .map_err(|e| anyhow::anyhow!("DeviceCollection::new(Capture): {e}"))?;
        collection.get_device_with_name(&device_name)
            .unwrap_or_else(|_| {
                let def = get_default_device(&Direction::Capture).expect("no default capture device");
                let def_name = def.get_friendlyname().unwrap_or_else(|_| "unknown".into());
                let _ = app.emit("engine-error", serde_json::json!({
                    "message": format!("Capture device '{device_name}' not found — fell back to '{def_name}'.")
                }));
                def
            })
    };

    let dev_name = device.get_friendlyname().unwrap_or_else(|_| "unknown".into());
    elog!(app, "MicCapture: device = '{dev_name}'");

    let mut audio_client = device
        .get_iaudioclient()
        .map_err(|e| anyhow::anyhow!("IAudioClient: {e}"))?;

    let mix_fmt = audio_client
        .get_mixformat()
        .map_err(|e| anyhow::anyhow!("get_mixformat: {e}"))?;

    let native_channels = mix_fmt.get_nchannels() as usize;
    let bytes_per_frame = mix_fmt.get_blockalign() as usize;
    let bits_per_sample = mix_fmt.get_bitspersample();
    let is_float        = matches!(mix_fmt.get_subformat(), Ok(SampleType::Float));

    elog!(app,
        "MicCapture: {}Hz ×{}ch {}bit {}",
        mix_fmt.get_samplespersec(), native_channels, bits_per_sample,
        if is_float { "float" } else { "int" }
    );

    let (_def_period, min_period) = audio_client
        .get_periods()
        .map_err(|e| anyhow::anyhow!("get_periods: {e}"))?;

    // Open as a standard capture stream — NOT loopback.
    audio_client
        .initialize_client(
            &mix_fmt,
            min_period as i64,
            &Direction::Capture,
            &ShareMode::Shared,
            false,
        )
        .map_err(|e| anyhow::anyhow!("initialize_client: {e}"))?;

    let h_event = audio_client
        .set_get_eventhandle()
        .map_err(|e| anyhow::anyhow!("set_get_eventhandle: {e}"))?;

    let capture_client = audio_client
        .get_audiocaptureclient()
        .map_err(|e| anyhow::anyhow!("get_audiocaptureclient: {e}"))?;

    audio_client
        .start_stream()
        .map_err(|e| anyhow::anyhow!("start_stream: {e}"))?;

    elog!(app, "MicCapture: capture loop running on '{dev_name}'");

    const TARGET_CH:    usize = 2;
    const CHUNK_FRAMES: usize = 480;

    let mut raw_buf: Vec<u8>  = vec![0u8; CHUNK_FRAMES * bytes_per_frame * 8];
    let mut queue:   Vec<f32> = Vec::with_capacity(CHUNK_FRAMES * TARGET_CH * 8);

    while !stop.load(Ordering::SeqCst) {
        h_event.wait_for_event(100).ok();

        loop {
            let nbr_frames = match capture_client
                .get_next_nbr_frames()
                .map_err(|e| anyhow::anyhow!("get_next_nbr_frames: {e}"))?
            {
                Some(n) if n > 0 => n as usize,
                _ => break,
            };

            let needed = nbr_frames * bytes_per_frame;
            if raw_buf.len() < needed { raw_buf.resize(needed, 0u8); }

            let (frames_read, flags) = capture_client
                .read_from_device(bytes_per_frame, &mut raw_buf[..needed])
                .map_err(|e| anyhow::anyhow!("read_from_device: {e}"))?;

            if frames_read == 0 { break; }

            let n_raw = frames_read as usize * native_channels;
            let native_f32: Vec<f32> = if flags.silent {
                vec![0.0f32; n_raw]
            } else if is_float && bits_per_sample == 32 {
                bytemuck::cast_slice::<u8, f32>(&raw_buf[..frames_read as usize * bytes_per_frame])
                    [..n_raw].to_vec()
            } else if !is_float && bits_per_sample == 16 {
                raw_buf[..frames_read as usize * bytes_per_frame]
                    .chunks_exact(2)
                    .map(|b| i16::from_le_bytes([b[0], b[1]]) as f32 / 32768.0)
                    .collect()
            } else if !is_float && bits_per_sample == 24 {
                raw_buf[..frames_read as usize * bytes_per_frame]
                    .chunks_exact(3)
                    .map(|b| { let v = i32::from_le_bytes([b[0], b[1], b[2], 0]) >> 8; v as f32 / 8_388_608.0 })
                    .collect()
            } else if !is_float && bits_per_sample == 32 {
                bytemuck::cast_slice::<u8, i32>(&raw_buf[..frames_read as usize * bytes_per_frame])
                    [..n_raw].iter().map(|&s| s as f32 / 2_147_483_648.0).collect()
            } else {
                eerr!(app, "MicCapture: unhandled format {}bit {}", bits_per_sample,
                    if is_float { "float" } else { "int" });
                vec![0.0f32; n_raw]
            };

            let stereo: Vec<f32> = if native_channels == TARGET_CH {
                native_f32
            } else if native_channels == 1 {
                native_f32.iter().flat_map(|&s| [s, s]).collect()
            } else {
                native_f32.chunks_exact(native_channels).flat_map(|c| [c[0], c[1]]).collect()
            };

            queue.extend_from_slice(&stereo);
        }

        while queue.len() >= CHUNK_FRAMES * TARGET_CH {
            let chunk: Vec<f32> = queue.drain(..CHUNK_FRAMES * TARGET_CH).collect();
            if tx.try_send(chunk).is_err() {
                if !stop.load(Ordering::SeqCst) {
                    eerr!(app, "MicCapture: channel full or disconnected — stopping");
                }
                stop.store(true, Ordering::SeqCst);
                break;
            }
        }
    }

    audio_client.stop_stream().ok();
    elog!(app, "MicCapture: stream stopped");
    Ok(())
}

#[cfg(not(target_os = "windows"))]
pub fn mic_capture_thread(
    _device_name: String,
    _tx:          Sender<Vec<f32>>,
    _stop:        Arc<AtomicBool>,
    _app:         tauri::AppHandle,
) -> Result<()> {
    anyhow::bail!("WASAPI mic capture is Windows-only")
}

// ── App-process loopback capture (Windows only) ───────────────────────────────

/// Resolve which render device `process_name` is using, then loopback-capture it.
/// Returns `Err` if the process is not found / not playing audio (monitor will retry).
#[cfg(target_os = "windows")]
pub fn app_loopback_capture_thread(
    process_name: String,
    tx:           Sender<Vec<f32>>,
    stop:         Arc<AtomicBool>,
    app:          tauri::AppHandle,
) -> Result<()> {
    elog!(app, "AppCapture: resolving process '{process_name}' → render device");
    match find_device_for_process(&process_name) {
        Some(device_name) => {
            elog!(app, "AppCapture: '{process_name}' is using render device '{device_name}'");
            loopback_capture_thread(device_name, tx, stop, app)
        }
        None => Err(anyhow::anyhow!(
            "process '{process_name}' not found or not playing audio — will retry"
        )),
    }
}

#[cfg(not(target_os = "windows"))]
pub fn app_loopback_capture_thread(
    _process_name: String,
    _tx:           Sender<Vec<f32>>,
    _stop:         Arc<AtomicBool>,
    _app:          tauri::AppHandle,
) -> Result<()> {
    anyhow::bail!("app loopback capture is Windows-only")
}

/// Spawn a temporary MTA thread to enumerate WASAPI sessions and return the
/// friendly name of the render device that `process_name` (case-insensitive
/// exe stem, e.g. "Spotify") is currently using.  Returns `None` if not found.
#[cfg(windows)]
fn find_device_for_process(process_name: &str) -> Option<String> {
    let name = process_name.to_lowercase();
    std::thread::spawn(move || unsafe { find_device_for_process_inner(&name) })
        .join()
        .ok()
        .flatten()
}

#[cfg(windows)]
unsafe fn find_device_for_process_inner(process_name: &str) -> Option<String> {
    use wasapi::{DeviceCollection, Direction};
    use windows::core::Interface as _;
    use windows::Win32::Foundation::BOOL;
    use windows::Win32::Media::Audio::{
        eRender, AudioSessionState, IAudioSessionControl2, IAudioSessionEnumerator,
        IAudioSessionManager2, IMMDeviceCollection, IMMDeviceEnumerator,
        MMDeviceEnumerator, DEVICE_STATE_ACTIVE,
    };
    use windows::Win32::System::Com::{
        CoCreateInstance, CoInitializeEx, CoUninitialize, CLSCTX_ALL, COINIT_MULTITHREADED,
    };
    use windows::Win32::System::Threading::{
        OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_WIN32,
        PROCESS_QUERY_LIMITED_INFORMATION,
    };

    let _ = CoInitializeEx(None, COINIT_MULTITHREADED);

    let result = (|| -> Option<String> {
        let enumerator: IMMDeviceEnumerator =
            CoCreateInstance(&MMDeviceEnumerator, None, CLSCTX_ALL).ok()?;
        let raw_coll: IMMDeviceCollection =
            enumerator.EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE).ok()?;
        let device_count = raw_coll.GetCount().ok()?;

        // wasapi DeviceCollection uses the same EnumAudioEndpoints order.
        let wasapi_coll = DeviceCollection::new(&Direction::Render).ok()?;

        for dev_idx in 0..device_count {
            let device = match raw_coll.Item(dev_idx) {
                Ok(d)  => d,
                Err(_) => continue,
            };
            let mgr: IAudioSessionManager2 = match device.Activate(CLSCTX_ALL, None) {
                Ok(m)  => m,
                Err(_) => continue,
            };
            let sess_enum: IAudioSessionEnumerator = match mgr.GetSessionEnumerator() {
                Ok(e)  => e,
                Err(_) => continue,
            };
            let sess_count = match sess_enum.GetCount() {
                Ok(n)  => n,
                Err(_) => continue,
            };

            for sess_idx in 0..sess_count {
                let ctrl = match sess_enum.GetSession(sess_idx) {
                    Ok(c)  => c,
                    Err(_) => continue,
                };
                if let Ok(state) = ctrl.GetState() {
                    if state == AudioSessionState(2) { continue; }
                }
                let ctrl2: IAudioSessionControl2 = match ctrl.cast() {
                    Ok(c)  => c,
                    Err(_) => continue,
                };
                let pid = match ctrl2.GetProcessId() {
                    Ok(p)  => p,
                    Err(_) => continue,
                };
                if pid == 0 { continue; }

                let handle = match OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, BOOL(0), pid) {
                    Ok(h)  => h,
                    Err(_) => continue,
                };
                let mut buf = [0u16; 260];
                let mut len = buf.len() as u32;
                let ok = QueryFullProcessImageNameW(
                    handle,
                    PROCESS_NAME_WIN32,
                    windows::core::PWSTR(buf.as_mut_ptr()),
                    &mut len,
                );
                let _ = windows::Win32::Foundation::CloseHandle(handle);
                if ok.is_err() { continue; }

                let path = String::from_utf16_lossy(&buf[..len as usize]);
                let stem = std::path::Path::new(&path)
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("")
                    .to_lowercase();

                if stem == process_name {
                    if let Ok(wasapi_dev) = wasapi_coll.get_device_at_index(dev_idx) {
                        if let Ok(friendly) = wasapi_dev.get_friendlyname() {
                            return Some(friendly);
                        }
                    }
                }
            }
        }

        None
    })();

    CoUninitialize();
    result
}
