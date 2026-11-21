# Sprint 18: Equity Curve chart in tkinter
# Run:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint18.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host ""
Write-Host "=== Sprint 18 Bootstrap: Equity Curve ===" -ForegroundColor Green

# --------------------------------------------------
# 1. Install matplotlib
# --------------------------------------------------
Write-Host "Installing matplotlib..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pip install matplotlib --quiet

# --------------------------------------------------
# 2. Patch native_gui.py: add equity chart
# --------------------------------------------------
$guiPath = Join-Path $root "src\native_gui.py"
$c = [System.IO.File]::ReadAllText($guiPath, [System.Text.Encoding]::UTF8)

# Add matplotlib import
$importAnchor = "import tkinter as tk"
$importBlock = @'
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
'@
if ($c.Contains("matplotlib.figure")) {
    Write-Host "matplotlib import already present"
} elseif ($c.Contains($importAnchor)) {
    $c = $c.Replace($importAnchor, $importBlock)
    Write-Host "Added matplotlib imports"
} else {
    Write-Host "WARN: tkinter import not found" -ForegroundColor Yellow
}

# Add equity chart to status view
$oldStatusBuild = @'
        # Activity
        tk.Label(frame, text="Activity", fg=self.accent, bg=self.bg, font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)
        self.activity_text = scrolledtext.ScrolledText(frame, bg="#2a2a2a", fg=self.fg, font=("Consolas", 9), height=8, wrap=tk.WORD)
        self.activity_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        return frame
'@
$newStatusBuild = @'
        # Equity Curve
        tk.Label(frame, text="Equity Curve", fg=self.accent, bg=self.bg, font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)
        self.equity_frame = tk.Frame(frame, bg=self.bg)
        self.equity_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Activity
        tk.Label(frame, text="Activity", fg=self.accent, bg=self.bg, font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)
        self.activity_text = scrolledtext.ScrolledText(frame, bg="#2a2a2a", fg=self.fg, font=("Consolas", 9), height=6, wrap=tk.WORD)
        self.activity_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        return frame
'@
if ($c.Contains($oldStatusBuild)) {
    $c = $c.Replace($oldStatusBuild, $newStatusBuild)
    Write-Host "Added equity chart frame to status view"
} else {
    Write-Host "WARN: status build anchor not found" -ForegroundColor Yellow
}

# Add equity chart refresh method
$refreshMethodAnchor = "    def _refresh_logs(self):"
$equityRefreshMethod = @'
    def _refresh_equity(self):
        """Draw equity curve from closed trades."""
        # Clear previous chart
        for widget in self.equity_frame.winfo_children():
            widget.destroy()
        
        trades = self._load_trades()
        closed = [t for t in trades if t.get("status") == "closed" and t.get("closed_at")]
        if not closed:
            tk.Label(self.equity_frame, text="No closed trades yet.", fg=self.grey, bg=self.bg, font=("Arial", 10)).pack(pady=20)
            return
        
        # Sort by closed_at
        closed.sort(key=lambda x: x.get("closed_at", 0))
        
        # Calculate cumulative PnL
        times = []
        cumulative_pnl = []
        running_total = 0.0
        for t in closed:
            ca = t.get("closed_at", 0)
            pnl = t.get("pnl") or 0
            running_total += pnl
            times.append(datetime.fromtimestamp(ca))
            cumulative_pnl.append(running_total)
        
        # Create matplotlib figure
        fig = Figure(figsize=(8, 3), dpi=100, facecolor=self.bg)
        ax = fig.add_subplot(111, facecolor=self.bg)
        ax.plot(times, cumulative_pnl, color=self.green, linewidth=2, marker='o', markersize=4)
        ax.set_title("Cumulative PnL", color=self.fg, fontsize=12, pad=10)
        ax.set_xlabel("Time", color=self.grey, fontsize=10)
        ax.set_ylabel("PnL (USDT)", color=self.grey, fontsize=10)
        ax.tick_params(colors=self.grey, labelsize=9)
        ax.spines['bottom'].set_color(self.grey)
        ax.spines['left'].set_color(self.grey)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.3, color=self.grey)
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.equity_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _refresh_logs(self):
'@
if ($c.Contains($refreshMethodAnchor)) {
    $c = $c.Replace($refreshMethodAnchor, $equityRefreshMethod)
    Write-Host "Added _refresh_equity method"
} else {
    Write-Host "WARN: refresh method anchor not found" -ForegroundColor Yellow
}

# Call equity refresh in _refresh_status
$oldRefreshStatus = @'
        # Update activity
        self.activity_text.delete(1.0, tk.END)
        self.activity_text.insert(tk.END, "".join(self._cache.get("logs", [])))
'@
$newRefreshStatus = @'
        # Update activity
        self.activity_text.delete(1.0, tk.END)
        self.activity_text.insert(tk.END, "".join(self._cache.get("logs", [])))
        
        # Update equity chart
        self._refresh_equity()
'@
if ($c.Contains($oldRefreshStatus)) {
    $c = $c.Replace($oldRefreshStatus, $newRefreshStatus)
    Write-Host "Added equity refresh call"
} else {
    Write-Host "WARN: status refresh anchor not found" -ForegroundColor Yellow
}

[System.IO.File]::WriteAllText($guiPath, $c, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Saved native_gui.py"

Write-Host ""
Write-Host "=== Sprint 18 finished ===" -ForegroundColor Green
Write-Host "Restart: close window, then .\START.bat"
Write-Host ""