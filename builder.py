import os
import subprocess
import time

# --- C APP FINAL BUILDER (NO GRADLEW REQUIRED) ---

GITHUB_REPO = "https://github.com/alwansan/C-App.git"
PACKAGE_NAME = "com.alwansan.c_app"

def run_command(command):
    print(f"🔄 CMD: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ OK")
        return True
    else:
        print(f"ℹ️ Info/Error: {result.stderr.strip()}")
        return False

def write_file(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"📄 Generated: {path}")

print("🛠️ Building App Structure...")

# 1. ROOT build.gradle.kts
write_file("build.gradle.kts", """
plugins {
    id("com.android.application") version "8.2.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.20" apply false
    id("com.google.devtools.ksp") version "1.9.20-1.0.14" apply false
}
""")

# 2. SETTINGS.gradle.kts
write_file("settings.gradle.kts", """
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "C-App"
include(":app")
""")

# 3. APP build.gradle.kts (تحديث تلقائي للإصدار)
current_time = int(time.time())
write_file("app/build.gradle.kts", f"""
plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
}}

android {{
    namespace = "{PACKAGE_NAME}"
    compileSdk = 34

    defaultConfig {{
        applicationId = "{PACKAGE_NAME}"
        minSdk = 26
        targetSdk = 34
        versionCode = {current_time}
        versionName = "1.0.{current_time}"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }}

    buildTypes {{
        release {{
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }}
    }}
    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }}
    kotlinOptions {{ jvmTarget = "1.8" }}
    buildFeatures {{ viewBinding = true }}
}}

dependencies {{
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    val room_version = "2.6.1"
    implementation("androidx.room:room-runtime:$room_version")
    implementation("androidx.room:room-ktx:$room_version")
    ksp("androidx.room:room-compiler:$room_version")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
}}
""")

# 4. gradle.properties
write_file("gradle.properties", """
org.gradle.jvmargs=-Xmx4g -Dfile.encoding=UTF-8
android.useAndroidX=true
android.enableJetifier=true
""")

# 5. GitHub Workflow (الحل السحري هنا)
# قمنا بإزالة الاعتماد على ./gradlew واستخدمنا gradle مباشرة
write_file(".github/workflows/android.yml", """
name: Android CI

on:
  push:
    branches: [ "main" ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up JDK 17
      uses: actions/setup-java@v4
      with:
        java-version: '17'
        distribution: 'temurin'

    # هذا السطر يثبت Gradle في السيرفر بدلاً من استخدام الملف المفقود
    - name: Setup Gradle
      uses: gradle/actions/setup-gradle@v3
      with:
        gradle-version: '8.5'

    # نستخدم أمر gradle مباشرة بدلاً من ./gradlew
    - name: Build APK
      run: gradle assembleDebug

    - name: Upload APK
      uses: actions/upload-artifact@v4
      with:
        name: C-App-Debug
        path: app/build/outputs/apk/debug/app-debug.apk
""")

# 6. Database Code
write_file(f"app/src/main/java/{PACKAGE_NAME.replace('.', '/')}/data/Database.kt", f"""
package {PACKAGE_NAME}.data
import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow
@Entity(tableName = "clips", indices = [Index(value = ["content"], unique = false)])
data class Clip(@PrimaryKey(autoGenerate = true) val id: Long = 0, val content: String, val timestamp: Long = System.currentTimeMillis(), val isPinned: Boolean = false, val folder: String = "Inbox")
@Dao interface ClipDao {{
    @Query("SELECT * FROM clips WHERE content LIKE '%' || :query || '%' ORDER BY isPinned DESC, timestamp DESC") fun search(query: String): Flow<List<Clip>>
    @Query("SELECT * FROM clips WHERE folder = :folderName ORDER BY isPinned DESC, timestamp DESC") fun getByFolder(folderName: String): Flow<List<Clip>>
    @Insert(onConflict = OnConflictStrategy.IGNORE) suspend fun insert(clip: Clip)
    @Delete suspend fun delete(clip: Clip)
    @Update suspend fun update(clip: Clip)
    @Query("SELECT DISTINCT folder FROM clips") fun getFolders(): Flow<List<String>>
    @Query("SELECT COUNT(*) FROM clips WHERE content = :txt") suspend fun countExact(txt: String): Int
}}
@Database(entities = [Clip::class], version = 1, exportSchema = false) abstract class AppDatabase : RoomDatabase() {{
    abstract fun dao(): ClipDao
    companion object {{ @Volatile private var INSTANCE: AppDatabase? = null
        fun get(context: Context): AppDatabase {{ return INSTANCE ?: synchronized(this) {{ Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, "c_app_db").fallbackToDestructiveMigration().build().also {{ INSTANCE = it }} }} }}
    }}
}}
""")

# 7. Background Service
write_file(f"app/src/main/java/{PACKAGE_NAME.replace('.', '/')}/service/ClipService.kt", f"""
package {PACKAGE_NAME}.service
import android.app.*
import android.content.*
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import {PACKAGE_NAME}.MainActivity
import {PACKAGE_NAME}.R
import {PACKAGE_NAME}.data.AppDatabase
import {PACKAGE_NAME}.data.Clip
class ClipService : Service(), ClipboardManager.OnPrimaryClipChangedListener {{
    private val scope = CoroutineScope(Dispatchers.IO); private lateinit var cm: ClipboardManager
    override fun onCreate() {{ super.onCreate(); cm = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager; cm.addPrimaryClipChangedListener(this); startForeground(1, createNotification()) }}
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY
    override fun onPrimaryClipChanged() {{ val clip = cm.primaryClip; if (clip != null && clip.itemCount > 0) {{ val text = clip.getItemAt(0).text?.toString()?.trim(); if (!text.isNullOrEmpty()) saveText(text) }} }}
    private fun saveText(text: String) {{ scope.launch {{ val dao = AppDatabase.get(applicationContext).dao(); if (dao.countExact(text) == 0) dao.insert(Clip(content = text)) }} }}
    private fun createNotification(): Notification {{
        val chanId = "c_service"; val chan = NotificationChannel(chanId, "C Listener", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(chan)
        val pend = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, chanId).setContentTitle("C Active").setSmallIcon(android.R.drawable.ic_menu_save).setContentIntent(pend).build()
    }}
    override fun onDestroy() {{ super.onDestroy(); cm.removePrimaryClipChangedListener(this) }}
    override fun onBind(intent: Intent?): IBinder? = null
}}
""")

# 8. Boot Receiver
write_file(f"app/src/main/java/{PACKAGE_NAME.replace('.', '/')}/service/BootReceiver.kt", f"""
package {PACKAGE_NAME}.service
import android.content.BroadcastReceiver; import android.content.Context; import android.content.Intent
class BootReceiver : BroadcastReceiver() {{
    override fun onReceive(context: Context, intent: Intent) {{ if (intent.action == Intent.ACTION_BOOT_COMPLETED) context.startForegroundService(Intent(context, ClipService::class.java)) }}
}}
""")

# 9. Main Activity
write_file(f"app/src/main/java/{PACKAGE_NAME.replace('.', '/')}/MainActivity.kt", f"""
package {PACKAGE_NAME}
import android.content.*; import android.os.Bundle; import android.view.*; import android.widget.*
import androidx.appcompat.app.AlertDialog; androidx.appcompat.app.AppCompatActivity; androidx.core.widget.addTextChangedListener
import androidx.lifecycle.lifecycleScope; androidx.recyclerview.widget.LinearLayoutManager; androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.launch; {PACKAGE_NAME}.data.*; {PACKAGE_NAME}.service.ClipService
class MainActivity : AppCompatActivity() {{
    private lateinit var adapter: CAdapter; private lateinit var db: AppDatabase; private var curFolder = "Inbox"
    override fun onCreate(savedInstanceState: Bundle?) {{ super.onCreate(savedInstanceState); setContentView(R.layout.activity_main); startForegroundService(Intent(this, ClipService::class.java)); db = AppDatabase.get(this); setupUI() }}
    private fun setupUI() {{
        val rv = findViewById<RecyclerView>(R.id.rvClips); val etSearch = findViewById<EditText>(R.id.etSearch); val btnFolder = findViewById<Button>(R.id.btnFolder)
        adapter = CAdapter(onClick = {{ copyToClip(it.content) }}, onLong = {{ showOpts(it) }}); rv.layoutManager = LinearLayoutManager(this); rv.adapter = adapter
        load(curFolder, ""); etSearch.addTextChangedListener {{ load(curFolder, it.toString()) }}
        btnFolder.setOnClickListener {{ lifecycleScope.launch {{ db.dao().getFolders().collect {{ folders -> val list = (folders + "Inbox").distinct().toTypedArray(); AlertDialog.Builder(this@MainActivity).setItems(list) {{ _, i -> curFolder = list[i]; btnFolder.text = curFolder; load(curFolder, "") }}.show() }} }} }}
    }}
    private fun load(folder: String, query: String) {{ lifecycleScope.launch {{ if (query.isNotEmpty()) db.dao().search(query).collect {{ adapter.submit(it) }} else db.dao().getByFolder(folder).collect {{ adapter.submit(it) }} }} }}
    private fun copyToClip(txt: String) {{ val cm = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager; cm.setPrimaryClip(ClipData.newPlainText("C", txt)); Toast.makeText(this, "Copied!", Toast.LENGTH_SHORT).show() }}
    private fun showOpts(clip: Clip) {{ val opts = arrayOf(if (clip.isPinned) "Unpin" else "Pin", "Move Folder", "Delete"); AlertDialog.Builder(this).setItems(opts) {{ _, i -> lifecycleScope.launch {{ when(i) {{ 0 -> db.dao().update(clip.copy(isPinned = !clip.isPinned)); 1 -> moveFolder(clip); 2 -> db.dao().delete(clip) }} }} }}.show() }}
    private fun moveFolder(clip: Clip) {{ val et = EditText(this); AlertDialog.Builder(this).setView(et).setTitle("New Folder").setPositiveButton("OK") {{ _, _ -> val f = et.text.toString().trim(); if(f.isNotEmpty()) lifecycleScope.launch {{ db.dao().update(clip.copy(folder = f)) }} }}.show() }}
}}
class CAdapter(val onClick: (Clip)->Unit, val onLong: (Clip)->Unit) : RecyclerView.Adapter<CAdapter.VH>() {{
    var list = listOf<Clip>(); fun submit(l: List<Clip>) {{ list = l; notifyDataSetChanged() }}
    class VH(v: View): RecyclerView.ViewHolder(v) {{ val tv: TextView = v.findViewById(R.id.tvTxt); val pin: View = v.findViewById(R.id.ivPin) }}
    override fun onCreateViewHolder(p: ViewGroup, t: Int) = VH(LayoutInflater.from(p.context).inflate(R.layout.item_c, p, false))
    override fun onBindViewHolder(h: VH, i: Int) {{ val c = list[i]; h.tv.text = c.content; h.pin.visibility = if (c.isPinned) View.VISIBLE else View.GONE; h.itemView.setOnClickListener {{ onClick(c) }}; h.itemView.setOnLongClickListener {{ onLong(c); true }} }}
    override fun getItemCount() = list.size
}}
""")

# 10. Layouts & Manifest
write_file("app/src/main/res/layout/activity_main.xml", """<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android" android:layout_width="match_parent" android:layout_height="match_parent" android:orientation="vertical" android:background="#000000" android:padding="10dp"><LinearLayout android:layout_width="match_parent" android:layout_height="wrap_content"><Button android:id="@+id/btnFolder" android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="Inbox" /><EditText android:id="@+id/etSearch" android:layout_width="match_parent" android:layout_height="50dp" android:hint="Search..." android:textColor="#FFF" android:textColorHint="#555" android:background="#222" /></LinearLayout><androidx.recyclerview.widget.RecyclerView android:id="@+id/rvClips" android:layout_width="match_parent" android:layout_height="match_parent" android:layout_marginTop="10dp"/></LinearLayout>""")
write_file("app/src/main/res/layout/item_c.xml", """<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android" android:layout_width="match_parent" android:layout_height="wrap_content" android:orientation="horizontal" android:padding="15dp" android:layout_margin="2dp" android:background="#1A1A1A"><TextView android:id="@+id/tvTxt" android:layout_width="0dp" android:layout_weight="1" android:layout_height="wrap_content" android:textColor="#EEE" android:maxLines="3"/><ImageView android:id="@+id/ivPin" android:layout_width="20dp" android:layout_height="20dp" android:src="@android:drawable/btn_star_big_on" android:visibility="gone"/></LinearLayout>""")
write_file("app/src/main/res/values/strings.xml", """<resources><string name="app_name">C</string></resources>""")
write_file("app/src/main/AndroidManifest.xml", """<?xml version="1.0" encoding="utf-8"?><manifest xmlns:android="http://schemas.android.com/apk/res/android"><uses-permission android:name="android.permission.FOREGROUND_SERVICE" /><uses-permission android:name="android.permission.POST_NOTIFICATIONS" /><uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" /><uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW"/><uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" /><application android:name=".CApp" android:label="C" android:theme="@style/Theme.AppCompat.NoActionBar"><activity android:name=".MainActivity" android:exported="true" android:windowSoftInputMode="adjustResize"><intent-filter><action android:name="android.intent.action.MAIN" /><category android:name="android.intent.category.LAUNCHER" /></intent-filter></activity><service android:name=".service.ClipService" android:foregroundServiceType="dataSync" /><receiver android:name=".service.BootReceiver" android:exported="true"><intent-filter><action android:name="android.intent.action.BOOT_COMPLETED"/></intent-filter></receiver></application></manifest>""")

print("✅ File Generation Complete.")

# --- SMART GIT LOGIC ---
print("\n🔄 Starting Smart Git Process...")

current_dir = os.getcwd()
run_command(f'git config --global --add safe.directory "{current_dir}"')

if not os.path.exists(".git"):
    run_command("git init")

run_command("git add .")

status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
if status.stdout.strip():
    run_command(f'git commit -m "Auto Update: {current_time}"')
else:
    print("ℹ️ No new changes.")

run_command("git branch -M main")

remote_check = subprocess.run("git remote get-url origin", shell=True, capture_output=True)
if remote_check.returncode == 0:
    run_command(f"git remote set-url origin {GITHUB_REPO}")
else:
    run_command(f"git remote add origin {GITHUB_REPO}")

print("🚀 Pushing to GitHub...")
run_command("git push -u origin main --force")

print("\n🎉 MISSION COMPLETE")