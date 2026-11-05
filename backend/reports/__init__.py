"""
PDF Reporting Subsystem.

Creates the forensic PDF that is uploaded after each analysis. The report is
designed to read like an official case document while preserving the raw model
signals returned by the API.
"""
import base64
import hashlib
import html
import io
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

try:
    import httpx
except Exception:
    httpx = None

REPORT_HASH_PLACEHOLDER = "REPORT_HASH_PLACEHOLDER"
DEFAULT_HARDHAT_CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
logger = logging.getLogger(__name__)


def _get_nested(data: dict, *keys: str, default: Any = None) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_percent(value: Any, digits: int = 1) -> str:
    number = _as_float(value)
    if number is None:
        return "Not available"
    return f"{number * 100:.{digits}f}%"


def _format_number(value: Any, digits: int = 6) -> str:
    number = _as_float(value)
    if number is None:
        return "Not available"
    return f"{number:.{digits}f}"


def _format_timestamp(value: Any) -> str:
    if not value:
        dt = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = datetime.now(timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M:%S UTC")


def _verdict_color(prediction: str, band: str) -> str:
    prediction_key = prediction.lower()
    band_key = band.lower()
    if "ai-generated" in prediction_key:
        return "#5b21b6"
    if "strong fake" in band_key or "manipulated" in prediction_key:
        return "#b91c1c"
    if "likely fake" in band_key:
        return "#c2410c"
    if "unsure" in band_key or "inconclusive" in prediction_key:
        return "#a16207"
    return "#047857"


def _risk_label(prediction: str, band: str) -> str:
    prediction_key = prediction.lower()
    band_key = band.lower()
    if "ai-generated" in prediction_key:
        return "Synthetic media indicators detected"
    if "manipulated" in prediction_key or "fake" in band_key:
        return "Manipulation indicators detected"
    if "inconclusive" in prediction_key or "unsure" in band_key:
        return "Manual review recommended"
    return "No strong manipulation indicators detected"


def _verdict_confidence(analysis_result: dict) -> float | None:
    prediction = str(analysis_result.get("prediction", "")).lower()
    details = analysis_result.get("details") or {}
    ucf_prob = _as_float(details.get("ucf_prob", analysis_result.get("confidence")))
    ai_prob = _as_float(details.get("ai_prob"))

    if "ai-generated" in prediction:
        return ai_prob
    if "authentic" in prediction and ucf_prob is not None:
        return 1.0 - ucf_prob
    if "manipulated" in prediction:
        return ucf_prob
    return None


def _confidence_note(analysis_result: dict) -> str:
    prediction = str(analysis_result.get("prediction", "")).lower()
    if "ai-generated" in prediction:
        return "Based on the AI-generated image detector probability."
    if "authentic" in prediction:
        return "Computed as one minus the UCF manipulation probability."
    if "manipulated" in prediction:
        return "Based on the UCF manipulation probability."
    return "The result falls between the configured real and fake thresholds."


def _heatmap_markup(heatmap_url: Any) -> str:
    if httpx is None:
        return '<div class="placeholder">Heatmap unavailable</div>'

    if isinstance(heatmap_url, str) and heatmap_url.startswith("https://"):
        try:
            response = httpx.get(heatmap_url, timeout=15)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/png").split(";")[0]
            encoded = base64.b64encode(response.content).decode("ascii")
            return f'<img class="heatmap" src="data:{content_type};base64,{encoded}" alt="Grad-CAM++ heatmap">'
        except Exception:
            pass

    return '<div class="placeholder">Heatmap unavailable</div>'


def _qr_markup(analysis_result: dict, report_hash: str) -> str:
    payload = str(
        analysis_result.get("polygon_url")
        or analysis_result.get("report_url")
        or (
            f"deepshield://analysis/{analysis_result.get('analysis_id', '')}"
            f"?report_hash={report_hash}"
            f"&file_hash={analysis_result.get('file_hash', '')}"
        )
    )

    try:
        import qrcode
    except Exception:
        return """
        <div class="qr-fallback">
          QR code support is not installed. Add the qrcode package to enable document verification QR codes.
        </div>
        """

    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f'<img class="qr" src="data:image/png;base64,{encoded}" alt="Verification QR code">'


def _generate_qr_base64(analysis_id: str, base_url: str = "") -> str:
    """
    Generate a QR code for the verification URL and return as base64 PNG.
    The QR code encodes the full verification URL.
    """
    try:
        import qrcode

        if base_url:
            verification_url = f"{base_url.rstrip('/')}/verify/{analysis_id}"
        else:
            verification_url = f"http://localhost:8000/verify/{analysis_id}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=6,
            border=2,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    except Exception as e:
        logger.error(f"[Reports] QR code generation failed: {e}")
        return ""


def _raw_logits(details: dict) -> str:
    logits = details.get("raw_logits")
    if not isinstance(logits, list) or not logits:
        return "Not available"
    return ", ".join(_format_number(value, 4) for value in logits)


def _history_markup(analysis_result: dict, analysis_id: str) -> str:
    prior = analysis_result.get("prior_analyses") or []
    if not prior:
        return ""

    rows = []
    for entry in prior:
        marker = "Current" if str(entry.get("id")) == str(analysis_id) else "Previous"
        rows.append(
            "<tr>"
            f"<td>{html.escape(marker)}</td>"
            f"<td>{html.escape(_format_timestamp(entry.get('created_at')))}</td>"
            f"<td>{html.escape(str(entry.get('prediction', 'Not available')))}</td>"
            f"<td>{html.escape(str(entry.get('band', 'Not available')))}</td>"
            f"<td>{html.escape(_format_percent(entry.get('confidence'), 3))}</td>"
            "</tr>"
        )

    return f"""
    <section>
      <div class="section-title">
        <h2>Submission History</h2>
        <span>{'Duplicate file detected' if analysis_result.get('is_duplicate') else 'First known submission'}</span>
      </div>
      <table>
        <thead>
          <tr><th>Status</th><th>Submission Date</th><th>Verdict</th><th>Band</th><th>UCF Probability</th></tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def _video_details_markup(analysis_result: dict) -> str:
    if analysis_result.get("type") != "video":
        return ""

    details = analysis_result.get("details") or {}
    return f"""
    <div class="subsection">
      <h3>Video Metrics</h3>
      <dl class="data-grid">
        <dt>Frame Count</dt><dd>{html.escape(str(details.get('frame_count', 'Not available')))}</dd>
        <dt>Aggregation Method</dt><dd>{html.escape(str(details.get('aggregation_method', 'Not available')))}</dd>
        <dt>Mean Frame Probability</dt><dd>{html.escape(_format_percent(_get_nested(details, 'xception_metrics', 'mean')))}</dd>
        <dt>Peak Frame Probability</dt><dd>{html.escape(_format_percent(_get_nested(details, 'xception_metrics', 'max')))}</dd>
        <dt>High-Risk Frame Fraction</dt><dd>{html.escape(_format_percent(_get_nested(details, 'xception_metrics', 'fhigh')))}</dd>
      </dl>
    </div>
    """


def _build_blockchain_section(
    analysis_result: dict,
    report_hash: str,
    analysis_id: str,
) -> str:
    blockchain_status = str(analysis_result.get("blockchain_status", "pending")).lower()
    tx_hash = str(
        analysis_result.get("blockchain_tx_hash")
        or analysis_result.get("transaction_hash")
        or ""
    )
    block_number = analysis_result.get("block_number", "")
    contract_address = str(
        analysis_result.get("contract")
        or analysis_result.get("contract_address")
        or DEFAULT_HARDHAT_CONTRACT_ADDRESS
    )

    qr_base64 = _generate_qr_base64(analysis_id) if analysis_id else ""

    if blockchain_status == "confirmed" and tx_hash:
        block_display = str(block_number) if block_number else "-"
        status_color = "#16a34a"
        status_label = "CONFIRMED"
        status_note = "This report hash has been anchored on-chain."
    else:
        tx_hash = ""
        block_display = "-"
        status_color = "#d97706"
        status_label = "PENDING"
        status_note = "Blockchain anchoring in progress. Check back shortly."

    qr_html = f"""
        <img src="{qr_base64}"
             style="width:100px; height:100px; display:block; margin:8px 0;"
             alt="Verification QR Code" />
        <p style="font-size:9px; color:#6b7280; margin:0;">
            Scan to verify on DeepShield
        </p>
    """ if qr_base64 else "<p style='font-size:9px;color:#9ca3af;'>QR unavailable</p>"

    return f"""
    <section>
      <div style="margin-top:24px; border:1px solid #e2e8f0; border-radius:8px;
                  padding:16px; background:#f8fafc; page-break-inside:avoid;">

          <h3 style="font-size:13px; font-weight:700; color:#1e3a5f;
                     margin:0 0 12px 0; border-bottom:1px solid #e2e8f0;
                     padding-bottom:8px;">
              Blockchain Anchoring Record
          </h3>

          <table style="width:100%; font-size:11px; border-collapse:collapse;">
              <tr>
                  <td style="padding:4px 8px 4px 0; color:#6b7280; width:160px; vertical-align:top;">
                      Status
                  </td>
                  <td style="padding:4px 0; font-weight:700; color:{status_color};">
                      {status_label} - {html.escape(status_note)}
                  </td>
              </tr>
              <tr>
                  <td style="padding:4px 8px 4px 0; color:#6b7280; vertical-align:top;">
                      Transaction Hash
                  </td>
                  <td style="padding:4px 0; font-family:monospace; font-size:10px; color:#1e293b;
                             word-break:break-all;">
                      {html.escape(tx_hash) if tx_hash else "&mdash;"}
                  </td>
              </tr>
              <tr>
                  <td style="padding:4px 8px 4px 0; color:#6b7280; vertical-align:top;">
                      Block Number
                  </td>
                  <td style="padding:4px 0; font-family:monospace; font-size:10px; color:#1e293b;">
                      {html.escape(block_display)}
                  </td>
              </tr>
              <tr>
                  <td style="padding:4px 8px 4px 0; color:#6b7280; vertical-align:top;">
                      Report Hash (SHA-256)
                  </td>
                  <td style="padding:4px 0; font-family:monospace; font-size:10px; color:#1e293b;
                             word-break:break-all;">
                      {html.escape(report_hash)}
                  </td>
              </tr>
              <tr>
                  <td style="padding:4px 8px 4px 0; color:#6b7280; vertical-align:top;">
                      Chain
                  </td>
                  <td style="padding:4px 0; color:#1e293b;">
                      DeepShield Private Chain (EVM-compatible, Chain ID: 31337)
                  </td>
              </tr>
              <tr>
                  <td style="padding:4px 8px 4px 0; color:#6b7280; vertical-align:top;">
                      Contract Address
                  </td>
                  <td style="padding:4px 0; font-family:monospace; font-size:10px; color:#1e293b;
                             word-break:break-all;">
                      {html.escape(contract_address) if contract_address else "&mdash;"}
                  </td>
              </tr>
              <tr>
                  <td style="padding:4px 8px 4px 0; color:#6b7280; vertical-align:top;">
                      Analysis ID
                  </td>
                  <td style="padding:4px 0; font-family:monospace; font-size:10px; color:#1e293b;">
                      {html.escape(analysis_id) if analysis_id else "&mdash;"}
                  </td>
              </tr>
          </table>

          <div style="margin-top:16px; display:flex; gap:16px; align-items:flex-start;">
              <div>
                  {qr_html}
              </div>
              <div style="font-size:10px; color:#64748b; line-height:1.6; max-width:300px;">
                  <strong style="color:#1e293b;">How to verify:</strong><br/>
                  1. Scan the QR code or visit the verification URL<br/>
                  2. Compare the Report Hash shown above with the hash
                     returned by the verification endpoint<br/>
                  3. If they match, the report has not been tampered with<br/>
                  4. The transaction hash proves the hash was recorded at
                     a specific block timestamp
              </div>
          </div>

          <p style="font-size:9px; color:#9ca3af; margin-top:12px; margin-bottom:0;
                    font-style:italic;">
              The SHA-256 hash of this report is anchored on an EVM-compatible blockchain.
              Anchoring occurred after report generation. This document is forensic
              evidence and should be retained securely.
          </p>
      </div>
    </section>
    """


def _build_html(analysis_result: dict, report_hash: str, analysis_id: str = "") -> str:
    analysis_id = str(analysis_id or analysis_result.get("analysis_id") or uuid.uuid4())
    created_at = _format_timestamp(analysis_result.get("created_at"))
    generated_at = _format_timestamp(datetime.now(timezone.utc))
    filename = str(analysis_result.get("filename", "Not available"))
    media_type = str(analysis_result.get("type", "Not available")).title()
    prediction = str(analysis_result.get("prediction", "Inconclusive"))
    band = str(analysis_result.get("band", _get_nested(analysis_result, "details", "band", default="Unsure")))
    details = analysis_result.get("details") or {}
    thresholds = analysis_result.get("thresholds") or {}
    verdict_color = _verdict_color(prediction, band)
    verdict_confidence = _verdict_confidence(analysis_result)
    ucf_probability = details.get("ucf_prob", analysis_result.get("confidence"))
    ai_probability = details.get("ai_prob")
    blockchain_section = _build_blockchain_section(analysis_result, report_hash, analysis_id)

    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>DeepShield Forensic Analysis Report</title>
      <style>
        @page {{
          size: A4;
          margin: 18mm 16mm;
          @bottom-center {{
            content: "DeepShield Forensic Analysis Report | Page " counter(page) " of " counter(pages);
            color: #64748b;
            font-size: 9px;
          }}
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          color: #111827;
          background: #ffffff;
          font-family: Arial, Helvetica, sans-serif;
          font-size: 11px;
          line-height: 1.45;
        }}
        .document {{
          border: 1px solid #cbd5e1;
        }}
        .masthead {{
          display: grid;
          grid-template-columns: 1fr 150px;
          gap: 20px;
          padding: 22px 24px;
          color: #ffffff;
          background: #0f172a;
          border-bottom: 5px solid {verdict_color};
        }}
        .wordmark {{
          font-size: 25px;
          font-weight: 800;
          letter-spacing: 0;
          margin-bottom: 5px;
        }}
        .doc-title {{
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 1.4px;
          text-transform: uppercase;
          color: #cbd5e1;
        }}
        .doc-meta {{
          margin-top: 18px;
          display: grid;
          grid-template-columns: 105px 1fr;
          gap: 4px 10px;
          color: #e5e7eb;
        }}
        .doc-meta dt {{
          margin: 0;
          color: #94a3b8;
          font-weight: 700;
        }}
        .doc-meta dd {{ margin: 0; overflow-wrap: anywhere; }}
        .classification {{
          border: 1px solid rgba(255, 255, 255, 0.22);
          padding: 12px;
          align-self: start;
          text-align: center;
        }}
        .classification-label {{
          color: #cbd5e1;
          font-size: 9px;
          font-weight: 700;
          letter-spacing: 1px;
          text-transform: uppercase;
        }}
        .classification-value {{
          margin-top: 8px;
          color: #ffffff;
          font-size: 14px;
          font-weight: 800;
        }}
        .content {{ padding: 20px 24px 24px; }}
        section {{
          margin-top: 16px;
          break-inside: avoid;
        }}
        section:first-child {{ margin-top: 0; }}
        .section-title {{
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 16px;
          padding-bottom: 7px;
          border-bottom: 1px solid #cbd5e1;
          margin-bottom: 12px;
        }}
        h2 {{
          margin: 0;
          color: #0f172a;
          font-size: 13px;
          font-weight: 800;
          letter-spacing: 0.4px;
          text-transform: uppercase;
        }}
        h3 {{
          margin: 14px 0 8px;
          color: #1f2937;
          font-size: 11px;
          font-weight: 800;
          text-transform: uppercase;
        }}
        .section-title span {{
          color: #64748b;
          font-size: 10px;
          font-weight: 700;
        }}
        .executive {{
          display: grid;
          grid-template-columns: 1.1fr 0.9fr;
          gap: 16px;
        }}
        .verdict-panel {{
          border: 1px solid #cbd5e1;
          padding: 16px;
          background: #f8fafc;
        }}
        .verdict-label {{
          color: #64748b;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.8px;
          text-transform: uppercase;
        }}
        .verdict {{
          margin-top: 7px;
          color: {verdict_color};
          font-size: 25px;
          font-weight: 800;
        }}
        .risk-label {{
          margin-top: 6px;
          color: #334155;
          font-size: 12px;
          font-weight: 700;
        }}
        .note {{
          margin-top: 9px;
          color: #475569;
          font-size: 10px;
        }}
        .metric-row {{
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-top: 14px;
        }}
        .metric {{
          border: 1px solid #dbe3ee;
          padding: 10px;
          background: #ffffff;
        }}
        .metric .name {{
          color: #64748b;
          font-size: 9px;
          font-weight: 800;
          text-transform: uppercase;
        }}
        .metric .value {{
          margin-top: 5px;
          color: #0f172a;
          font-size: 15px;
          font-weight: 800;
        }}
        .data-card {{
          border: 1px solid #cbd5e1;
          padding: 14px;
        }}
        .data-grid {{
          display: grid;
          grid-template-columns: 38% 62%;
          gap: 7px 12px;
          margin: 0;
        }}
        .data-grid dt {{
          margin: 0;
          color: #475569;
          font-weight: 800;
        }}
        .data-grid dd {{
          margin: 0;
          overflow-wrap: anywhere;
        }}
        .subsection {{
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #e2e8f0;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          font-size: 10px;
        }}
        th, td {{
          padding: 7px 8px;
          border: 1px solid #e2e8f0;
          text-align: left;
          vertical-align: top;
        }}
        th {{
          color: #334155;
          background: #f1f5f9;
          font-weight: 800;
        }}
        .heatmap-wrap {{
          border: 1px solid #cbd5e1;
          padding: 10px;
          background: #f8fafc;
          text-align: center;
        }}
        .heatmap {{
          display: block;
          max-width: 100%;
          max-height: 310px;
          margin: 0 auto;
          border: 1px solid #cbd5e1;
        }}
        .placeholder {{
          height: 230px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #64748b;
          background: #e5e7eb;
          font-weight: 800;
        }}
        .caption {{
          margin-top: 8px;
          color: #64748b;
          font-size: 10px;
          text-align: left;
        }}
        .verification {{
          display: grid;
          grid-template-columns: 1fr 112px;
          gap: 16px;
          align-items: start;
        }}
        .qr {{
          width: 108px;
          height: 108px;
          border: 1px solid #cbd5e1;
          padding: 5px;
        }}
        .qr-fallback {{
          width: 108px;
          min-height: 108px;
          border: 1px solid #cbd5e1;
          padding: 8px;
          color: #64748b;
          font-size: 9px;
        }}
        .hash {{
          font-family: Consolas, Monaco, monospace;
          font-size: 9px;
          overflow-wrap: anywhere;
        }}
        .smallprint {{
          margin-top: 12px;
          padding-top: 10px;
          border-top: 1px solid #e2e8f0;
          color: #64748b;
          font-size: 9px;
        }}
        a {{ color: #1d4ed8; text-decoration: none; }}
      </style>
    </head>
    <body>
      <div class="document">
        <header class="masthead">
          <div>
            <div class="wordmark">DeepShield</div>
            <div class="doc-title">Forensic Analysis Report</div>
            <dl class="doc-meta">
              <dt>Analysis ID</dt><dd>{html.escape(analysis_id)}</dd>
              <dt>Generated</dt><dd>{html.escape(generated_at)}</dd>
              <dt>Analyzed</dt><dd>{html.escape(created_at)}</dd>
              <dt>Filename</dt><dd>{html.escape(filename)}</dd>
            </dl>
          </div>
          <div class="classification">
            <div class="classification-label">Media Classification</div>
            <div class="classification-value">{html.escape(media_type)}</div>
          </div>
        </header>

        <main class="content">
          <section>
            <div class="section-title">
              <h2>Executive Summary</h2>
              <span>{html.escape(_risk_label(prediction, band))}</span>
            </div>
            <div class="executive">
              <div class="verdict-panel">
                <div class="verdict-label">Final Verdict</div>
                <div class="verdict">{html.escape(prediction)}</div>
                <div class="risk-label">Forensic Band: {html.escape(band)}</div>
                <div class="note">{html.escape(_confidence_note(analysis_result))}</div>
              </div>
              <div class="data-card">
                <dl class="data-grid">
                  <dt>Verdict Confidence</dt><dd>{html.escape(_format_percent(verdict_confidence, 1))}</dd>
                  <dt>UCF Manipulation Probability</dt><dd>{html.escape(_format_percent(ucf_probability, 3))}</dd>
                  <dt>AI-Generated Probability</dt><dd>{html.escape(_format_percent(ai_probability, 2))}</dd>
                  <dt>Processing Time</dt><dd>{html.escape(str(analysis_result.get('processing_time_seconds', 'Not available')))} seconds</dd>
                  <dt>Duplicate Submission</dt><dd>{'Yes' if analysis_result.get('is_duplicate') else 'No'}</dd>
                </dl>
              </div>
            </div>
            <div class="metric-row">
              <div class="metric">
                <div class="name">Real Threshold</div>
                <div class="value">{html.escape(_format_percent(thresholds.get('real'), 0))}</div>
              </div>
              <div class="metric">
                <div class="name">Fake Threshold</div>
                <div class="value">{html.escape(_format_percent(thresholds.get('fake'), 0))}</div>
              </div>
              <div class="metric">
                <div class="name">API Confidence Field</div>
                <div class="value">{html.escape(_format_percent(analysis_result.get('confidence'), 3))}</div>
              </div>
            </div>
          </section>

          <section>
            <div class="section-title">
              <h2>Model Evidence</h2>
              <span>Raw detector outputs</span>
            </div>
            <div class="data-card">
              <dl class="data-grid">
                <dt>Primary Model</dt><dd>{html.escape(str(details.get('model', 'Not available')).upper())}</dd>
                <dt>UCF Probability</dt><dd>{html.escape(_format_percent(ucf_probability, 3))}</dd>
                <dt>AI Detector Probability</dt><dd>{html.escape(_format_percent(ai_probability, 2))}</dd>
                <dt>Raw Logits</dt><dd>{html.escape(_raw_logits(details))}</dd>
                <dt>Frame Count</dt><dd>{html.escape(str(details.get('frame_count', 'Not applicable')))}</dd>
                <dt>Aggregation Method</dt><dd>{html.escape(str(details.get('aggregation_method', 'Not applicable')))}</dd>
              </dl>
              {_video_details_markup(analysis_result)}
            </div>
          </section>

          <section>
            <div class="section-title">
              <h2>Visual Explainability</h2>
              <span>Grad-CAM++ activation heatmap</span>
            </div>
            <div class="heatmap-wrap">
              {_heatmap_markup(analysis_result.get('heatmap_url'))}
              <div class="caption">
                Highlighted regions indicate image areas that influenced the model output. The heatmap is interpretive evidence and should be reviewed alongside the probability scores.
              </div>
            </div>
          </section>

          {_history_markup(analysis_result, analysis_id)}

          <section>
            <div class="section-title">
              <h2>Verification and Integrity</h2>
              <span>Document fingerprint</span>
            </div>
            <div class="verification">
              <div class="data-card">
                <dl class="data-grid">
                  <dt>File SHA-256</dt><dd class="hash">{html.escape(str(analysis_result.get('file_hash', 'Not available')))}</dd>
                  <dt>Report SHA-256</dt><dd class="hash">{html.escape(report_hash)}</dd>
                </dl>
                <div class="smallprint">
                  This report is generated by DeepShield for forensic reference and audit support. The report hash identifies this exact PDF. Use the blockchain anchoring record below to verify the stored hash against the corresponding on-chain record.
                </div>
              </div>
            </div>
          </section>

          {blockchain_section}
        </main>
      </div>
    </body>
    </html>
    """


def generate_pdf_report(
    analysis_result: dict,
    analysis_id: str = "",
    report_hash: str | None = None,
) -> tuple[bytes, str]:
    from weasyprint import HTML

    if report_hash is None:
        report_hash = compute_pdf_report_hash(analysis_result, analysis_id)

    final_html = _build_html(analysis_result, report_hash, analysis_id)
    final_pdf = HTML(string=final_html).write_pdf()
    return final_pdf, report_hash


def compute_pdf_report_hash(
    analysis_result: dict,
    analysis_id: str = "",
) -> str:
    """
    Compute the stable report fingerprint before final PDF rendering.

    The final PDF can include the blockchain transaction details that anchor
    this hash, avoiding reports that are uploaded before anchoring completes.
    """
    from weasyprint import HTML

    first_pass_html = _build_html(analysis_result, REPORT_HASH_PLACEHOLDER, analysis_id)
    first_pass_pdf = HTML(string=first_pass_html).write_pdf()
    return hashlib.sha256(first_pass_pdf).hexdigest()
