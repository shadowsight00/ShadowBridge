use anyhow::Result;
use cpal::{
    traits::{DeviceTrait, StreamTrait},
    Device, Stream, StreamConfig,
};
use crossbeam_channel::Receiver;
use parking_lot::Mutex;
use std::{
    collections::VecDeque,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};

pub struct PlaybackStream {
    _stream: Stream,
}

unsafe impl Send for PlaybackStream {}

impl PlaybackStream {
    /// `prebuffer_samples` — number of interleaved f32 samples to accumulate before
    /// the audio callback starts draining (absorbs initial network jitter).
    pub fn new(
        device: &Device,
        config: &StreamConfig,
        rx: Receiver<Vec<f32>>,
        prebuffer_samples: usize,
    ) -> Result<Self> {
        let buf: Arc<Mutex<VecDeque<f32>>> =
            Arc::new(Mutex::new(VecDeque::with_capacity(96_000)));

        let ready = Arc::new(AtomicBool::new(false));

        let buf_fill  = Arc::clone(&buf);
        let ready_set = Arc::clone(&ready);
        std::thread::spawn(move || {
            for chunk in rx {
                let mut b = buf_fill.lock();
                b.extend(chunk.iter().copied());

                if !ready_set.load(Ordering::Relaxed) && b.len() >= prebuffer_samples {
                    ready_set.store(true, Ordering::Release);
                }

                // Cap at ~2 s of stereo 48 kHz.
                while b.len() > 192_000 {
                    b.pop_front();
                }
            }
        });

        let buf_drain   = Arc::clone(&buf);
        let ready_check = Arc::clone(&ready);
        let stream = device.build_output_stream(
            config,
            move |out: &mut [f32], _| {
                if !ready_check.load(Ordering::Acquire) {
                    out.fill(0.0);
                    return;
                }
                if let Some(mut b) = buf_drain.try_lock() {
                    for o in out.iter_mut() {
                        *o = b.pop_front().unwrap_or(0.0);
                    }
                } else {
                    out.fill(0.0);
                }
            },
            |err| log::error!("playback stream error: {err}"),
            None,
        )?;
        stream.play()?;
        Ok(Self { _stream: stream })
    }
}
