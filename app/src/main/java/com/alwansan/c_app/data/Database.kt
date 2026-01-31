package com.alwansan.c_app.data

import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "clips", indices = [Index(value = ["content"], unique = false)])
data class Clip(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val content: String,
    val timestamp: Long = System.currentTimeMillis(),
    val isPinned: Boolean = false,
    val folder: String = "Inbox"
)

@Dao
interface ClipDao {
    @Query("SELECT * FROM clips WHERE content LIKE '%' || :query || '%' ORDER BY isPinned DESC, timestamp DESC")
    fun search(query: String): Flow<List<Clip>>

    @Query("SELECT * FROM clips WHERE folder = :folderName ORDER BY isPinned DESC, timestamp DESC")
    fun getByFolder(folderName: String): Flow<List<Clip>>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(clip: Clip)

    @Delete
    suspend fun delete(clip: Clip)

    @Update
    suspend fun update(clip: Clip)
    
    @Query("SELECT DISTINCT folder FROM clips")
    fun getFolders(): Flow<List<String>>

    @Query("SELECT COUNT(*) FROM clips WHERE content = :txt")
    suspend fun countExact(txt: String): Int
}

@Database(entities = [Clip::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun dao(): ClipDao
    
    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null
        fun get(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, "c_app_db")
                    .fallbackToDestructiveMigration()
                    .build().also { INSTANCE = it }
            }
        }
    }
}