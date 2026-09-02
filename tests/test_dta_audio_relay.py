from dta_autolive.infrastructure.dta_audio_relay import DTAAudioRelay


def test_dta_audio_relay_init():
    relay = DTAAudioRelay(sample_rate=44100, channels=2)
    assert relay.sample_rate == 44100
    assert relay.channels == 2
    assert not relay.is_running
    assert relay.volume == 1.0


def test_dta_audio_relay_find_ffmpeg():
    relay = DTAAudioRelay()
    bin_path = relay._find_ffmpeg()  # noqa: SLF001
    assert bin_path is not None
    assert len(bin_path) > 0


def test_dta_audio_relay_volume():
    relay = DTAAudioRelay()
    relay.set_volume(0.8)
    assert relay.volume == 0.8
    relay.set_volume(1.5)
    assert relay.volume == 1.0
    relay.set_volume(-0.5)
    assert relay.volume == 0.0


def test_dta_audio_relay_stop_when_idle():
    relay = DTAAudioRelay()
    relay.stop_audio_relay()
    assert not relay.is_running
