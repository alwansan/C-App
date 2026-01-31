package com.alwansan.c_app
import android.content.*; import android.os.Bundle; import android.view.*; import android.widget.*
import androidx.appcompat.app.AlertDialog; androidx.appcompat.app.AppCompatActivity; androidx.core.widget.addTextChangedListener
import androidx.lifecycle.lifecycleScope; androidx.recyclerview.widget.LinearLayoutManager; androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.launch; com.alwansan.c_app.data.*; com.alwansan.c_app.service.ClipService
class MainActivity : AppCompatActivity() {
    private lateinit var adapter: CAdapter; private lateinit var db: AppDatabase; private var curFolder = "Inbox"
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContentView(R.layout.activity_main); startForegroundService(Intent(this, ClipService::class.java)); db = AppDatabase.get(this); setupUI() }
    private fun setupUI() {
        val rv = findViewById<RecyclerView>(R.id.rvClips); val etSearch = findViewById<EditText>(R.id.etSearch); val btnFolder = findViewById<Button>(R.id.btnFolder)
        adapter = CAdapter(onClick = { copyToClip(it.content) }, onLong = { showOpts(it) }); rv.layoutManager = LinearLayoutManager(this); rv.adapter = adapter
        load(curFolder, ""); etSearch.addTextChangedListener { load(curFolder, it.toString()) }
        btnFolder.setOnClickListener { lifecycleScope.launch { db.dao().getFolders().collect { folders -> val list = (folders + "Inbox").distinct().toTypedArray(); AlertDialog.Builder(this@MainActivity).setItems(list) { _, i -> curFolder = list[i]; btnFolder.text = curFolder; load(curFolder, "") }.show() } } }
    }
    private fun load(folder: String, query: String) { lifecycleScope.launch { if (query.isNotEmpty()) db.dao().search(query).collect { adapter.submit(it) } else db.dao().getByFolder(folder).collect { adapter.submit(it) } } }
    private fun copyToClip(txt: String) { val cm = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager; cm.setPrimaryClip(ClipData.newPlainText("C", txt)); Toast.makeText(this, "Copied!", Toast.LENGTH_SHORT).show() }
    private fun showOpts(clip: Clip) { val opts = arrayOf(if (clip.isPinned) "Unpin" else "Pin", "Move Folder", "Delete"); AlertDialog.Builder(this).setItems(opts) { _, i -> lifecycleScope.launch { when(i) { 0 -> db.dao().update(clip.copy(isPinned = !clip.isPinned)); 1 -> moveFolder(clip); 2 -> db.dao().delete(clip) } } }.show() }
    private fun moveFolder(clip: Clip) { val et = EditText(this); AlertDialog.Builder(this).setView(et).setTitle("New Folder").setPositiveButton("OK") { _, _ -> val f = et.text.toString().trim(); if(f.isNotEmpty()) lifecycleScope.launch { db.dao().update(clip.copy(folder = f)) } }.show() }
}
class CAdapter(val onClick: (Clip)->Unit, val onLong: (Clip)->Unit) : RecyclerView.Adapter<CAdapter.VH>() {
    var list = listOf<Clip>(); fun submit(l: List<Clip>) { list = l; notifyDataSetChanged() }
    class VH(v: View): RecyclerView.ViewHolder(v) { val tv: TextView = v.findViewById(R.id.tvTxt); val pin: View = v.findViewById(R.id.ivPin) }
    override fun onCreateViewHolder(p: ViewGroup, t: Int) = VH(LayoutInflater.from(p.context).inflate(R.layout.item_c, p, false))
    override fun onBindViewHolder(h: VH, i: Int) { val c = list[i]; h.tv.text = c.content; h.pin.visibility = if (c.isPinned) View.VISIBLE else View.GONE; h.itemView.setOnClickListener { onClick(c) }; h.itemView.setOnLongClickListener { onLong(c); true } }
    override fun getItemCount() = list.size
}
