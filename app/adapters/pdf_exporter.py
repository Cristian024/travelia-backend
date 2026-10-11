import shutil
from pathlib import Path
from typing import Optional

from app.models.itinerary import ItineraryDocument
from app.ports.external import ItineraryExporterPort

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_KNOWN_PATHS = [
    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
    r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
    r"C:\wkhtmltopdf\bin\wkhtmltopdf.exe",
    "/usr/local/bin/wkhtmltopdf",
    "/usr/bin/wkhtmltopdf",
    "/opt/homebrew/bin/wkhtmltopdf",
]


def resolve_wkhtmltopdf(explicit_path: Optional[str] = None) -> Optional[str]:
    """Devuelve la ruta al binario wkhtmltopdf, o None si no se encuentra."""
    if explicit_path:
        candidate = Path(explicit_path)
        return str(candidate) if candidate.exists() else None

    found = shutil.which("wkhtmltopdf")
    if found:
        return found

    for candidate in _KNOWN_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


class PdfKitItineraryExporter(ItineraryExporterPort):
    """Renderiza el itinerario con Jinja2 y lo convierte a PDF con pdfkit.

    La ruta a `wkhtmltopdf` se resuelve explícitamente (param o autodetección)
    para no depender de que el binario esté en el PATH del proceso.
    """

    def __init__(
        self,
        template_name: str = "itinerary_pdf.html",
        wkhtmltopdf_path: Optional[str] = None,
    ) -> None:
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        self._template_name = template_name
        self._wkhtmltopdf_path = resolve_wkhtmltopdf(wkhtmltopdf_path)
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    @property
    def wkhtmltopdf_path(self) -> Optional[str]:
        return self._wkhtmltopdf_path

    async def to_pdf(self, itinerary: ItineraryDocument) -> bytes:
        import pdfkit

        if not self._wkhtmltopdf_path:
            raise RuntimeError(
                "No se encontró el binario 'wkhtmltopdf'."
            )

        config = pdfkit.configuration(wkhtmltopdf=self._wkhtmltopdf_path)
        template = self._env.get_template(self._template_name)
        html = template.render(itinerary=itinerary)

        options = {
            "page-size": "A4",
            "margin-top": "15mm",
            "margin-bottom": "15mm",
            "margin-left": "12mm",
            "margin-right": "12mm",
            "encoding": "UTF-8",
        }
        try:
            pdf = pdfkit.from_string(html, False, options=options, configuration=config)
        except OSError as exc:
            raise RuntimeError(
                f"No se pudo generar el PDF con wkhtmltopdf en '{self._wkhtmltopdf_path}'."
            ) from exc
        return pdf if isinstance(pdf, bytes) else bytes(pdf)
