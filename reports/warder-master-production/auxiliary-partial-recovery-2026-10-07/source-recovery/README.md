# Source recovery analysis

The four pinned legacy ZIPs were SHA/size/CRC verified. Black/White pairs were compared at exact aligned pixel coordinates. `SAFE-RECOVERABLE` requires exact RGBA equality including the alpha plane, identical visible support, and a transparent canvas. No thresholding, OCR, filename semantics, or external matching was used. Black-only variants remain unresolved; alpha and geometry are recorded but do not establish original colors. No production assets or downloads manifests were changed.
