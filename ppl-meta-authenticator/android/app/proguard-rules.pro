# shared_preferences_android 2.5+ looks up Kotlin stdlib classes by name via JNI.
# R8 renames them in release builds and prefs calls fail (NoSuchMethodError /
# "Shared preferences unavailable"). Keep these even if we stay on <2.5.0.
-keep class kotlin.Unit { *; }
-keep class kotlin.Result { *; }
-keep class kotlin.Result$Failure { *; }
-keep class kotlin.coroutines.Continuation { *; }
-keep class kotlin.coroutines.intrinsics.CoroutineSingletons { *; }
-keep class kotlin.coroutines.intrinsics.IntrinsicsKt { *; }
