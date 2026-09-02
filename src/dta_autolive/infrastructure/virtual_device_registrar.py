"""Windows DirectShow Virtual Camera & Audio Registrar Engine for DTA Studio."""

from dta_autolive.infrastructure.dta_driver_installer import DTADriverInstaller
from dta_autolive.infrastructure.dta_driver_setup import setup_dta_virtual_hardware_drivers


class VirtualDeviceRegistrar:
    """Manages 1-Click Installation & Registration of Windows Virtual Camera & Audio Drivers."""

    @staticmethod
    def register_dta_devices() -> tuple[bool, str, list[str]]:
        """Register DTA Camera and DTA Audio DirectShow Virtual Devices into Windows Driver Registry."""
        try:
            ok_setup, logs_setup = setup_dta_virtual_hardware_drivers()
            ok_pnp, logs_pnp = DTADriverInstaller.install_all_drivers()
            all_logs = logs_setup + logs_pnp
            msg = "Đã hoàn thành cài đặt gói PnPUtil INF Driver và ghi danh phần cứng DTA Camera & DTA Audio!"
            return ok_setup and ok_pnp, msg, all_logs
        except Exception as e:
            return (
                False,
                f"Lỗi đăng ký thiết bị: {e}",
                [f"[ERROR] Exception during registration: {e}"],
            )
