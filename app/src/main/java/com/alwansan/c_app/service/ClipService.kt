package com.alwansan.c_app.service
import android.app.*
import android.content.*
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import com.alwansan.c_app.MainActivity
import com.alwansan.c_app.data.AppDatabase
import com.alwansan.c_app.data.Clip
class ClipService : Service(), ClipboardManager.OnPrimaryClipChangedListener {
    private val scope = CoroutineScope(Dispatchers.IO); private lateinit var cm: ClipboardManager
    override fun onCreate() { super.onCreate(); cm = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager; cm.addPrimaryClipChangedListener(this); startForeground(1, createNotification()) }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY
    override fun onPrimaryClipChanged() { val clip = cm.primaryClip; if (clip != null && clip.itemCount > 0) { val text = clip.getItemAt(0).text?.toString()?.trim(); if (!text.isNullOrEmpty()) saveText(text) } }
    private fun saveText(text: String) { scope.launch { val dao = AppDatabase.get(applicationContext).dao(); if (dao.countExact(text) == 0) dao.insert(Clip(content = text)) } }
    private fun createNotification(): Notification {
        val chanId = "c_service"; val chan = NotificationChannel(chanId, "C Listener", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(chan)
        val pend = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, chanId).setContentTitle("C Active").setSmallIcon(android.R.drawable.ic_menu_save).setContentIntent(pend).build()
    }
    override fun onDestroy() { super.onDestroy(); cm.removePrimaryClipChangedListener(this) }
    override fun onBind(intent: Intent?): IBinder? = null
}
