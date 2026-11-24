import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setChromiumOpenGlRenderer((process.env.REMOTION_GL as "angle" | "egl" | "swangle" | "vulkan") || "angle");
Config.setConcurrency(1);
