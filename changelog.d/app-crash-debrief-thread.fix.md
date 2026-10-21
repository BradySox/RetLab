* **[UI]** Debrief, sim clock and saved-point updates reach the UI on its own thread. Sending them from other threads is the likely cause of the app closing with no error 20-40 s after a mission ended.
* **[UI]** A native crash writes every thread's Python stack to `logs/faulthandler.log`.
