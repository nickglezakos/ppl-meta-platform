package com.example.ppl_meta_frontend

import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.util.Log

/**
 * Helper class to manage codec compatibility on Android devices.
 * 
 * This specifically addresses issues with H.264 High Profile decoding
 * where hardware decoders may not properly support the profile or have
 * surface texture issues.
 */
object CodecHelper {
    private const val TAG = "PPL_CodecHelper"
    
    /**
     * Check if device supports H.264 High Profile decoding
     * Returns false if we detect known problematic hardware
     */
    fun supportsH264HighProfile(): Boolean {
        return try {
            val codecList = MediaCodecList(MediaCodecList.ALL_CODECS)
            val h264CodecInfo = codecList.codecInfos.firstOrNull { 
                it.name.contains("h264", ignoreCase = true) && !it.isEncoder
            }
            
            if (h264CodecInfo != null) {
                val supportedTypes = h264CodecInfo.supportedTypes
                val h264Type = supportedTypes.firstOrNull { it == "video/avc" }
                
                if (h264Type != null) {
                    val capabilities = h264CodecInfo.getCapabilitiesForType(h264Type)
                    val profileLevels = capabilities.profileLevels
                    
                    Log.d(TAG, "Found H.264 decoder: ${h264CodecInfo.name}")
                    Log.d(TAG, "Profiles: ${profileLevels.map { it.profile }.joinToString(",")}")
                    
                    // Check if High Profile (profile == 8) is present
                    val hasHighProfile = profileLevels.any { it.profile == 8 }
                    Log.d(TAG, "Supports H.264 High Profile: $hasHighProfile")
                    
                    // Check for known problematic devices
                    val hasKnownIssue = checkKnownProblematicDevices()
                    
                    return hasHighProfile && !hasKnownIssue
                }
            }
            false
        } catch (e: Exception) {
            Log.e(TAG, "Error checking H.264 High Profile support", e)
            false
        }
    }
    
    /**
     * Check for known Android devices with H.264 decoding issues
     */
    private fun checkKnownProblematicDevices(): Boolean {
        val manufacturer = android.os.Build.MANUFACTURER.lowercase()
        val model = android.os.Build.MODEL.lowercase()
        val device = android.os.Build.DEVICE.lowercase()
        
        // Known problematic device patterns
        val problematicPatterns = listOf(
            "samsung.*galaxy.*j" to "Samsung Galaxy J series",
            "samsung.*galaxy.*a[0-6]" to "Samsung Galaxy A1-A6 series",
            "xiaomi.*redmi.*4" to "Xiaomi Redmi 4",
            "lenovo" to "Lenovo devices (generic)",
            "huawei.*honor.*5" to "Huawei Honor 5 series",
        )
        
        Log.d(TAG, "Device: $manufacturer $model ($device)")
        
        return problematicPatterns.any { (pattern, name) ->
            val regex = Regex(pattern)
            val matches = regex.containsMatchIn("$manufacturer $model $device")
            if (matches) {
                Log.w(TAG, "Device matches known problematic pattern: $name")
            }
            matches
        }
    }
    
    /**
     * Get recommended H.264 profile for this device
     * Returns "baseline" for devices with known issues
     */
    fun getRecommendedH264Profile(): String {
        return if (supportsH264HighProfile()) {
            Log.i(TAG, "Device supports high profiles, not restricting codec")
            "main"
        } else {
            Log.w(TAG, "Device has issues, restricting to Baseline profile only")
            "baseline"
        }
    }
}
