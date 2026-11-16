"""Local PowerShell launcher contracts; no Reflex server or Xano requests."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/iniciar_nexstock_dev.ps1"
FLAGS = (
    "NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED",
    "NEXSTOCK_PURCHASE_NOTIFICATIONS_ENABLED",
    "NEXSTOCK_ACCOUNT_PASSWORD_ENABLED",
    "NEXSTOCK_PURCHASE_RECEIPTS_ENABLED",
    "NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED",
    "NEXSTOCK_PURCHASE_REQUEST_EMAIL_ENABLED",
)


class NexStockDevelopmentLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not cls.powershell:
            raise unittest.SkipTest("PowerShell indisponível para validar o launcher.")

    def test_launcher_preserves_feature_flag_overrides_during_launch_and_after_return_or_error(self):
        with tempfile.TemporaryDirectory(prefix="nexstock-launch-test-") as temp_name:
            temp = Path(temp_name)
            scripts = temp / "scripts"
            fake_reflex = temp / ".venv/Scripts/reflex-mock.ps1"
            scripts.mkdir()
            fake_reflex.parent.mkdir(parents=True)

            wrapper = scripts / LAUNCHER.name
            wrapper_source = LAUNCHER.read_text(encoding="utf-8").replace(
                r".venv\Scripts\reflex.exe", r".venv\Scripts\reflex-mock.ps1"
            )
            self.assertIn("reflex-mock.ps1", wrapper_source)
            wrapper.write_text(wrapper_source, encoding="utf-8")
            fake_reflex.write_text(
                """
$observed = [ordered]@{
  movements = $env:NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED
  notifications = $env:NEXSTOCK_PURCHASE_NOTIFICATIONS_ENABLED
  account_password = $env:NEXSTOCK_ACCOUNT_PASSWORD_ENABLED
  purchase_receipts = $env:NEXSTOCK_PURCHASE_RECEIPTS_ENABLED
  insufficient_summary = $env:NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED
  request_email = $env:NEXSTOCK_PURCHASE_REQUEST_EMAIL_ENABLED
}
[IO.File]::WriteAllText($env:NEXSTOCK_TEST_FLAGS_OUTPUT, ($observed | ConvertTo-Json -Compress))
if ($env:NEXSTOCK_TEST_THROW -eq 'true') { throw 'Simulated launcher failure.' }
""",
                encoding="utf-8",
            )

            observed_path = temp / "observed.json"
            command = f"""
$ErrorActionPreference = 'Stop'
$env:NEXSTOCK_TEST_FLAGS_OUTPUT = '{observed_path}'
Set-Location -LiteralPath $env:TEMP
try {{ . '{wrapper}' }} catch {{ $caught = $true; $caughtMessage = $_.Exception.Message }}
$restored = @(
  [Environment]::GetEnvironmentVariable('{FLAGS[0]}', 'Process'),
  [Environment]::GetEnvironmentVariable('{FLAGS[1]}', 'Process'),
  [Environment]::GetEnvironmentVariable('{FLAGS[2]}', 'Process'),
  [Environment]::GetEnvironmentVariable('{FLAGS[3]}', 'Process'),
  [Environment]::GetEnvironmentVariable('{FLAGS[4]}', 'Process'),
  [Environment]::GetEnvironmentVariable('{FLAGS[5]}', 'Process')
)
@{{ caught = [bool]$caught; message = $caughtMessage; restored = $restored }} | ConvertTo-Json -Compress
"""

            for should_throw in (False, True):
                with self.subTest(should_throw=should_throw):
                    prior_values = ("false", "custom-local-value", None, "false", "off", "custom-email-setting")
                    process_env = os.environ.copy()
                    for name, value in zip(FLAGS, prior_values):
                        if value is None:
                            process_env.pop(name, None)
                        else:
                            process_env[name] = value
                    process_env["NEXSTOCK_TEST_THROW"] = "true" if should_throw else "false"
                    observed_path.unlink(missing_ok=True)
                    result = subprocess.run(
                        [self.powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                        env=process_env,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True,
                    )
                    summary = json.loads(result.stdout.strip().splitlines()[-1])
                    self.assertEqual(summary["caught"], should_throw, summary.get("message"))
                    self.assertEqual(summary["restored"], list(prior_values))
                    self.assertTrue(observed_path.exists(), result.stderr + result.stdout)
                    observed = json.loads(observed_path.read_text(encoding="utf-8"))
                    self.assertEqual(list(observed.values()), list(prior_values))

    def test_runtime_validated_presentation_features_default_on_with_explicit_opt_out(self):
        source = r"""
import json
from Meu_projeto.pages.dashboard import REAL_DASHBOARD_MOVEMENTS_ENABLED, DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED
from Meu_projeto.state.dashboard_notifications import NOTIFICATIONS_ENABLED
from Meu_projeto.pages.account_password import ACCOUNT_PASSWORD_ENABLED
from Meu_projeto.services.purchase_receipts import PURCHASE_RECEIPTS_ENABLED
from Meu_projeto.pages.reposicao import _recipient_email_contract_enabled
print(json.dumps({
    "movements": REAL_DASHBOARD_MOVEMENTS_ENABLED,
    "notifications": NOTIFICATIONS_ENABLED,
    "account_password": ACCOUNT_PASSWORD_ENABLED,
    "receipts": PURCHASE_RECEIPTS_ENABLED,
    "insufficient_summary": DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED,
    "request_email": _recipient_email_contract_enabled(),
}))
"""
        defaults_env = os.environ.copy()
        for name in FLAGS:
            defaults_env.pop(name, None)
        defaults = subprocess.run(
            [sys.executable, "-c", source],
            cwd=ROOT,
            env=defaults_env,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        self.assertEqual(
            json.loads(defaults.stdout.strip().splitlines()[-1]),
            {
                "movements": True,
                "notifications": True,
                "account_password": False,
                "receipts": True,
                "insufficient_summary": False,
                "request_email": False,
            },
        )

        disabled_env = defaults_env.copy()
        disabled_env[FLAGS[0]] = "false"
        disabled_env[FLAGS[1]] = "false"
        disabled_env[FLAGS[3]] = "false"
        disabled = subprocess.run(
            [sys.executable, "-c", source],
            cwd=ROOT,
            env=disabled_env,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        disabled_values = json.loads(disabled.stdout.strip().splitlines()[-1])
        self.assertFalse(disabled_values["movements"])
        self.assertFalse(disabled_values["notifications"])
        self.assertFalse(disabled_values["receipts"])


if __name__ == "__main__":
    unittest.main()
