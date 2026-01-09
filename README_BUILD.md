# Building Maple Autocuber Executable

This guide explains how to build the Maple Autocuber bot into a standalone executable (.exe) file.

## Prerequisites

1. **Python 3.7+** installed
2. **All dependencies** from `requirements.txt` installed:
   ```bash
   pip install -r requirements.txt
   ```

3. **PyInstaller** (will be installed automatically by build script):
   ```bash
   pip install pyinstaller
   ```

4. **Tesseract OCR** - Portable version bundled:
   - A portable Tesseract installation should be in `tesseract/` folder at project root
   - The executable will automatically use the bundled Tesseract
   - Users don't need to install Tesseract separately

## Building the Executable

### Windows
Simply run:
```bash
build.bat
```

Or manually:
```bash
pyinstaller build_exe.spec
```

### Linux/Mac
```bash
chmod +x build.sh
./build.sh
```

Or manually:
```bash
pyinstaller build_exe.spec
```

## Output

The executable will be created in the `dist` folder:
- **Windows**: `dist\MapleAutocuber.exe`
- **Linux/Mac**: `dist/MapleAutocuber`

## Important Notes

1. **Tesseract OCR**: The executable includes a bundled portable Tesseract OCR. Users don't need to install Tesseract separately - it's automatically detected and used.

2. **Templates Folder**: The `templates` folder (containing `reset_button.jpg`) is automatically included in the build.

3. **Configuration**: The `crop_config.py` file is included in the build. Users can modify it if needed.

4. **Console Mode**: By default, the executable runs without a console window. To enable console output for debugging, change `console=False` to `console=True` in `build_exe.spec`.

5. **File Size**: The executable will be large (50-100MB+) because it includes Python and all dependencies. This is normal.

## Distribution

When distributing the executable:
1. Include the executable file (Tesseract is already bundled)
2. Include a README with usage instructions
3. Optionally include `crop_config.py` if users need to customize crop regions
4. No additional installation required - everything is bundled!

## Troubleshooting

### "Tesseract not found" error
- Ensure the `tesseract/` folder exists at project root and contains `tesseract.exe`
- The build process should automatically bundle Tesseract
- Check that `build_exe.spec` includes the tesseract folder in the `datas` section

### Missing DLL errors
- Ensure all required Windows DLLs are available
- May need to install Visual C++ Redistributable

### Large file size
- This is normal - PyInstaller bundles Python and all dependencies
- Consider using `--onefile` mode (already enabled) for single-file distribution

