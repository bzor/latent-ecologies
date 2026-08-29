// Font library: registers every font in fonts/ via injected @font-face rules
// (CSS path — works on file://, unlike FontFace fetch) and exposes the list
// for the preview's type pickers.
(function () {
  "use strict";

  window.FONT_LIBRARY = [
    { label: "Isonorm Monospaced", file: "Isonorm Monospaced Regular.otf" },
    { label: "Isonorm", file: "Isonorm Regular.otf" },
    { label: "Isonorm MN", file: "Isonorm MN Regular.ttf" },
    { label: "Iosevka Mono Thin", file: "IosevkaTermNerdFontMono-Thin.ttf" },
    { label: "Iosevka Mono ExtraLight", file: "IosevkaTermNerdFontMono-ExtraLight.ttf" },
    { label: "Iosevka Mono Light", file: "IosevkaTermNerdFontMono-Light.ttf" },
    { label: "Iosevka Mono Medium", file: "IosevkaTermNerdFontMono-Medium.ttf" },
    { label: "Iosevka Light", file: "IosevkaTermNerdFont-Light.ttf" },
    { label: "Blender Pro Book", file: "BlenderPro-Book.ttf" },
    { label: "Blender Pro Medium", file: "BlenderPro-Medium.otf" },
    { label: "Blender Pro Bold", file: "BlenderPro-Bold.ttf" },
    { label: "Helvetica Neue Md", file: "HelveticaNeueLTCom-Md.ttf" },
    { label: "Helvetica Neue Hv", file: "HelveticaNeueLTCom-Hv.ttf" },
    { label: "DIN Alternate Bold", file: "DIN Alternate Bold.ttf" },
    { label: "Arame Thin", file: "Arame Thin.ttf" },
    { label: "Dosis (variable)", file: "Dosis-VariableFont_wght.ttf" },
    { label: "APK Systema", file: "APKSystema_Regular.otf" },
    { label: "kroeger 07_56 (pixel)", file: "kroe0756.ttf" },
    { label: "schoenecker 10_56 (pixel)", file: "SCHO1056.TTF" },
    { label: "2DADEC A", file: "2DADEC_0_0.ttf" },
    { label: "2DADEC B", file: "2DADEC_1_0.ttf" },
  ];

  const css = window.FONT_LIBRARY.map((f) => {
    const fmt = /\.otf$/i.test(f.file) ? "opentype" : "truetype";
    return '@font-face { font-family: "' + f.label + '"; src: url("fonts/' +
      f.file + '") format("' + fmt + '"); }';
  }).join("\n");

  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);
})();
