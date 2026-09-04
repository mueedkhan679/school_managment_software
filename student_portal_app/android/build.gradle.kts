allprojects {
    repositories {
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

// Dynamic reflection method that works smoothly across AGP 8.x and AGP 9.x
subprojects {
    afterEvaluate {
        val androidExtension = project.extensions.findByName("android")
        if (androidExtension != null) {
            try {
                val setCompileSdk = androidExtension.javaClass.methods.firstOrNull {
                    it.name == "setCompileSdk" && it.parameterCount == 1 && it.parameterTypes[0] == Integer.TYPE
                }
                setCompileSdk?.invoke(androidExtension, 36)
            } catch (_: Exception) {}

            try {
                val setNdkVersion = androidExtension.javaClass.methods.firstOrNull {
                    it.name == "setNdkVersion" && it.parameterCount == 1 && it.parameterTypes[0] == String::class.java
                }
                setNdkVersion?.invoke(androidExtension, "")
            } catch (_: Exception) {}
        }
    }
}

subprojects {
    project.evaluationDependsOn(":app")

    tasks.withType<JavaCompile>().configureEach {
        sourceCompatibility = "17"
        targetCompatibility = "17"
    }
    
    tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}