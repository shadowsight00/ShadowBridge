use std::sync::{
    atomic::{AtomicBool, AtomicU32, Ordering},
    Arc,
};
use parking_lot::Mutex;
use crate::audio::meter::LevelMeter;

/// Live state for a single active audio channel.
pub struct ChannelStream {
    pub id: String,
    /// Volume stored as f32 bits to allow lock-free reads from audio threads.
    volume_bits: Arc<AtomicU32>,
    meter: Arc<Mutex<LevelMeter>>,
    pub stop_flag: Arc<AtomicBool>,
}

impl ChannelStream {
    pub fn new(id: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            volume_bits: Arc::new(AtomicU32::new(f32::to_bits(1.0))),
            meter: Arc::new(Mutex::new(LevelMeter::new(4800))),
            stop_flag: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn volume(&self) -> f32 {
        f32::from_bits(self.volume_bits.load(Ordering::Relaxed))
    }

    pub fn set_volume(&self, v: f32) {
        self.volume_bits
            .store(f32::to_bits(v.clamp(0.0, 1.0)), Ordering::Relaxed);
    }

    /// Scale samples by the current volume in-place.
    pub fn apply_volume(&self, samples: &mut [f32]) {
        let vol = self.volume();
        for s in samples.iter_mut() {
            *s *= vol;
        }
    }

    pub fn update_meter(&self, samples: &[f32]) {
        self.meter.lock().push(samples);
    }

    pub fn segments(&self) -> [bool; 14] {
        self.meter.lock().segments()
    }

    pub fn stop(&self) {
        self.stop_flag.store(true, Ordering::SeqCst);
    }

    /// Clone the stop flag so capture/playback threads can watch it.
    pub fn stop_flag(&self) -> Arc<AtomicBool> {
        Arc::clone(&self.stop_flag)
    }
}
