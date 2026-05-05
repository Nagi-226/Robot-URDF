# Robot URDF Studio v0.7.5 Packaging Checklist

- [ ] Build onefile: `./build.ps1 -Mode onefile -SkipInstall -SmokeTest`
- [ ] Build onedir debug package: `./build.ps1 -Mode onedir -SkipInstall -SmokeTest`
- [ ] Verify `dist/RobotURDFStudio.exe` metadata shows ProductName and ProductVersion
- [ ] Launch exe on clean Windows 11 host without console window
- [ ] Load `models/simple_arm.urdf` and `models/delta_bot.urdf`
- [ ] Toggle 2D/3D, move joint sliders, and export screenshot
- [ ] Verify package:// URDF meshes resolve in a ROS-style workspace
- [ ] Run dev signing: `scripts/sign_windows_dev.ps1 -CreateCertificate`
- [ ] Replace dev cert with release code-signing cert before public release
