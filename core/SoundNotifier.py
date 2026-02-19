import platform


class SoundNotifier:

    def __init__(self,
                 success_path="sounds/success.wav",
                 error_path="sounds/error.wav"):
        self.success_path = success_path
        self.error_path = error_path

    # =========================
    # PUBLIC
    # =========================

    def success(self):
        try:
            self._play(self.success_path)
        except Exception:
            self._fallback(success=True)

    def error(self):
        try:
            self._play(self.error_path)
        except Exception:
            self._fallback(success=False)

    # =========================
    # INTERNAL
    # =========================

    def _play(self, path):
        try:
            import simpleaudio as sa   # 👈 import ตรงนี้เท่านั้น
            wave = sa.WaveObject.from_wave_file(path)
            wave.play()
        except Exception:
            raise

    def _fallback(self, success=True):
        system = platform.system()

        if system == "Windows":
            import winsound
            if success:
                winsound.Beep(1500, 250)
                winsound.Beep(1800, 200)
            else:
                winsound.Beep(500, 700)
        else:
            print("\a" if success else "\a\a")
