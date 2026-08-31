allprojects {
    repositories {
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}

// Force compileSdk 36 on every subproject (including plugins like
// flutter_secure_storage that hardcode a lower compileSdk). This keeps all
// modules aligned with the app-level compileSdk = 36 and ensures transitive
// plugins (e.g. sqflite_android) compile against API 36, providing the
// Baklava symbols they reference (Build.VERSION_CODES.BAKLAVA).
subprojects {
    afterEvaluate {
        val androidExtension = project.extensions.findByName("android")
        if (androidExtension != null) {
            var forced = false
            try {
                val setCompileSdk = androidExtension.javaClass.methods.firstOrNull {
                    it.name == "setCompileSdk" && it.parameterCount == 1 &&
                        it.parameterTypes[0] == Integer.TYPE
                }
                if (setCompileSdk != null) {
                    setCompileSdk.invoke(androidExtension, 36)
                    forced = true
                }
            } catch (ignore: Exception) {
                // Ignore; try the legacy setter below.
            }
            if (!forced) {
                try {
                    val setCompileSdkVersion = androidExtension.javaClass.methods.firstOrNull {
                        it.name == "setCompileSdkVersion" && it.parameterCount == 1 &&
                            it.parameterTypes[0] == Integer.TYPE
                    }
                    if (setCompileSdkVersion != null) {
                        setCompileSdkVersion.invoke(androidExtension, 36)
                        forced = true
                    }
                } catch (ignore2: Exception) {
                    // Ignore; log and continue.
                }
            }
            if (!forced) {
                println("WARNING: could not force compileSdk=36 on project ${project.path}")
            }
        }
    }
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
