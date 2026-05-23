/// 14-segment RMS level meter matching the UI bar layout.
pub struct LevelMeter {
    window: Vec<f32>,
    pos: usize,
}

pub const NUM_SEGMENTS: usize = 14;

/// dB thresholds for each segment (bottom → top).
const THRESHOLDS_DB: [f32; NUM_SEGMENTS] = [
    -42.0, -36.0, -30.0, -24.0, -20.0, -18.0, -16.0,
    -14.0, -12.0, -9.0, -6.0, -3.0, -1.5, 0.0,
];

impl LevelMeter {
    pub fn new(window_samples: usize) -> Self {
        Self {
            window: vec![0.0_f32; window_samples],
            pos: 0,
        }
    }

    pub fn push(&mut self, samples: &[f32]) {
        let cap = self.window.len();
        for &s in samples {
            self.window[self.pos] = s * s;
            self.pos = (self.pos + 1) % cap;
        }
    }

    pub fn rms_db(&self) -> f32 {
        let mean_sq = self.window.iter().sum::<f32>() / self.window.len() as f32;
        if mean_sq < 1e-10 {
            return -96.0;
        }
        20.0 * mean_sq.sqrt().log10()
    }

    /// Normalised level 0.0 (silence) → 1.0 (0 dBFS), mapped from -60 dB..0 dB.
    pub fn level(&self) -> f32 {
        ((self.rms_db() + 60.0) / 60.0).clamp(0.0, 1.0)
    }

    /// Returns which of the 14 segments should be lit.
    pub fn segments(&self) -> [bool; NUM_SEGMENTS] {
        let db = self.rms_db();
        let mut out = [false; NUM_SEGMENTS];
        for (i, &thresh) in THRESHOLDS_DB.iter().enumerate() {
            out[i] = db >= thresh;
        }
        out
    }
}
