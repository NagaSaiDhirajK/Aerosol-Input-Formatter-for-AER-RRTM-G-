#!/usr/bin/env python
# coding: utf-8

from flask import Flask, render_template, request, Response
from io import StringIO

app = Flask(__name__)

#Formatting help
def one_digit_format(val, rng):
    return val[-1:] if val.isdigit() and (int(val) in range(rng + 1)) else 'NaN'

def two_digits_format(val):
    return ('0' + val) if val.isdigit() and len(val) == 1 else (val[-2:] if val.isdigit() else 'NaN')

def two_digits_format_without_0(val):
    return val if val.isdigit() and (len(val) in range(4) and int(val) / 100 < 0) else (val[-2:] if val.isdigit() else 'NaN')

def _format_line(values, widths):
    out = [f"{v:>{widths[i]}}" if widths and i < len(widths) else v for i, v in enumerate(values)]
    return "".join(out)

def is_float(val):
    try:
        float(val)
        return True
    except Exception:
        return False

def _float_digit(val, float_fmt, rng):
    return format(float(val), float_fmt) if is_float(val) and (0.0 <= float(val) <= float(rng)) else 'NaN'

#These functions help for validating the inputs from forms
def _as_int(s):
    try:
        return int(str(s).strip())
    except Exception:
        return None

def _as_float(s):
    try:
        return float(str(s).strip())
    except Exception:
        return None

def _in_range(val, lo, hi):
    return (val is not None) and (lo <= val <= hi)

def validate_aerosols(aerosols):
    errors = []
    naer = len(aerosols)
    if not (1 <= naer <= 99):
        errors.append(f"NAER must be between 1 and 99; got {naer}.")

    for i, aer in enumerate(aerosols, start=1):
        # Map IAOD/IOAD
        raw_iaod = str(aer.get("IAOD", aer.get("IOAD", ""))).strip()
        raw_issa = str(aer.get("ISSA", "")).strip()
        raw_ipha = str(aer.get("IPHA", "")).strip()
        raw_nlay = str(aer.get("NLAY", "")).strip()

        iaod = _as_int(raw_iaod)
        issa = _as_int(raw_issa)
        ipha = _as_int(raw_ipha)
        nlay = _as_int(raw_nlay)

        if iaod is None or iaod not in (0, 1):
            errors.append(f"[Aerosol {i}] IAOD must be 0 or 1; got {raw_iaod}.")
        if issa is None or issa not in (0, 1):
            errors.append(f"[Aerosol {i}] ISSA must be 0 or 1; got {raw_issa}.")
        if ipha is None or ipha not in (0, 1, 2):
            errors.append(f"[Aerosol {i}] IPHA must be 0, 1, or 2; got {raw_ipha}.")
        if nlay is None or not (0 <= nlay <= 51):
            errors.append(f"[Aerosol {i}] NLAY must be 0–51; got {raw_nlay}.")

        layers = aer.get("layers", [])
        if nlay is not None and len(layers) != (nlay or 0):
            errors.append(f"[Aerosol {i}] Provided {len(layers)} A2.1.1 layer records but NLAY={nlay}.")

        # Duplicate LAY check + parse and range
        seen = set()
        for j, layer in enumerate(layers, start=1):
            lay_raw = str(layer.get("layer", "")).strip()
            lay_int = _as_int(lay_raw)
            if lay_int is None or not (0 <= lay_int <= 999):  # spec says I3; practical range 0–999; doc mentions 0–51 typical
                errors.append(f"[Aerosol {i}] Layer {j}: LAY must be integer (0–999); got '{lay_raw}'.")
            if lay_int in seen:
                errors.append(f"[Aerosol {i}] Duplicate layer number detected: LAY={lay_int}. Each LAY must be unique.")
            else:
                seen.add(lay_int)

        # IAOD branches
        if iaod == 0:
            for p in ("AERPAR1", "AERPAR2", "AERPAR3"):
                val = _as_float(aer.get(p, ""))
                if not _in_range(val, 0.0, 1.0):
                    errors.append(f"[Aerosol {i}] {p} must be 0.00–1.00; got '{aer.get(p, '')}'.")
            for j, layer in enumerate(layers, start=1):
                aod1 = _as_float(layer.get("ioa", ""))
                if not _in_range(aod1, 0.0, 1.0):
                    errors.append(f"[Aerosol {i}] Layer {j}: AOD1 must be 0.0000–1.0000; got '{layer.get('ioa', '')}'.")
        elif iaod == 1:
            for j, layer in enumerate(layers, start=1):
                vals = layer.get("ioa", [])
                if not isinstance(vals, (list, tuple)) or len(vals) != 14:
                    errors.append(f"[Aerosol {i}] Layer {j}: must provide 14 AOD(IB) values for IB=16–29.")
                    continue
                for k, v in enumerate(vals, start=16):
                    vf = _as_float(v)
                    if not _in_range(vf, 0.0, 1.0):
                        errors.append(f"[Aerosol {i}] Layer {j}: AOD(IB={k}) must be 0.0000–1.0000; got '{v}'.")

        # A2.2 SSA
        if issa == 0:
            s = _as_float(aer.get("ssa", ""))
            if not _in_range(s, 0.0, 1.0):
                errors.append(f"[Aerosol {i}] SSA(16) must be 0.00–1.00; got '{aer.get('ssa', '')}'.")
        elif issa == 1:
            vals = aer.get("ssa", [])
            if not isinstance(vals, (list, tuple)) or len(vals) != 14:
                errors.append(f"[Aerosol {i}] SSA must have 14 values for IB=16–29 when ISSA=1.")
            else:
                for k, v in enumerate(vals, start=16):
                    vf = _as_float(v)
                    if not _in_range(vf, 0.0, 1.0):
                        errors.append(f"[Aerosol {i}] SSA(IB={k}) must be 0.00–1.00; got '{v}'.")
        #A2.1 and A2.3 IPHA but A2.3 Record is only needed for IPHA=2 and RRTMG does not allow DISORT, so check RRTMG instructions for more info.
        if ipha == 0:
            g16 = _as_float(aer.get("ipha", ""))
            if not _in_range(g16, 0.0, 1.0):
                errors.append(f"[Aerosol {i}] PHASE(16) (first moment/asymmetry) must be 0.00–1.00; got '{aer.get('ipha', '')}'.")
        else:
            vals = aer.get("ipha", [])
            if not isinstance(vals, (list, tuple)) or len(vals) != 14:
                errors.append(f"[Aerosol {i}] PHASE must have 14 values for IB=16–29 when IPHA={ipha}.")
            else:
                for k, v in enumerate(vals, start=16):
                    vf = _as_float(v) 
                    if not _in_range(vf, 0.0, 1.0):
                        errors.append(f"[Aerosol {i}] PHASE(IB={k}) must be 0.00–1.00; got '{v}'.")

    return errors

#Core builder
def build_aer_input(aerosols):
    output = []
    NAER = len(aerosols)
    NAER_fmt_digit = two_digits_format(str(NAER))[-1:]
    NAER_format = _format_line(list(NAER_fmt_digit), [5]) if len(_format_line(list(NAER_fmt_digit), [5])) == 5 else _format_line(list(NAER_fmt_digit), [4])
    output.append([NAER_format])

    for aer in aerosols:
        ind_aer_output = []

        NLAY_raw = str(aer.get("NLAY", "0"))
        IAOD_raw = str(aer.get("IAOD", aer.get("IOAD", "0")))  # accept IOAD but treat as IAOD
        ISSA_raw = str(aer.get("ISSA", "0"))
        IPHA_raw = str(aer.get("IPHA", "0"))

        NLAY = two_digits_format(NLAY_raw)
        IAOD = one_digit_format(IAOD_raw, 1)
        ISSA = one_digit_format(ISSA_raw, 1)
        IPHA = one_digit_format(IPHA_raw, 2)

        ind_aer_output.append([
            _format_line(list(NLAY), [4]),
            _format_line(list(IAOD), [5]),
            _format_line(list(ISSA), [5]),
            _format_line(list(IPHA), [5])
        ])

        aero_ioad_layer = []
        if int(IAOD_raw) == 0:
            AERPAR1 = _float_digit(str(aer.get("AERPAR1", "")), '1.2f', 1)
            AERPAR2 = _float_digit(str(aer.get("AERPAR2", "")), '1.2f', 1)
            AERPAR3 = _float_digit(str(aer.get("AERPAR3", "")), '1.2f', 1)
            ind_aer_output.append([
                _format_line(list(AERPAR1), [5]),
                _format_line(list(AERPAR2), [5]),
                _format_line(list(AERPAR3), [5]),
            ])

            for layer in aer.get("layers", []):
                layer_idx_fmt = two_digits_format_without_0(str(layer.get("layer", "")))
                val_fmt = _float_digit(str(layer.get("ioa", "")), '1.4f', 1) + '0'
                fmt_try_5 = _format_line(list(layer_idx_fmt), [5])
                if len(fmt_try_5) == 5:
                    formatted_layer = fmt_try_5
                else:
                    fmt_try_4 = _format_line(list(layer_idx_fmt), [4])
                    formatted_layer = fmt_try_4 if len(fmt_try_4) == 5 else _format_line(list(layer_idx_fmt), [3])
                aero_ioad_layer.append([formatted_layer, val_fmt])
            ind_aer_output.append(aero_ioad_layer)

        else:
            ind_aer_output.append([
                _format_line(list('0.00'), [5]),
                _format_line(list('0.00'), [5]),
                _format_line(list('0.00'), [5]),
            ])

            rows = []
            for layer in aer.get("layers", []):
                layer_idx_fmt = two_digits_format_without_0(str(layer.get("layer", "")))
                fmt_try_5 = _format_line(list(layer_idx_fmt), [5])
                if len(fmt_try_5) == 5:
                    formatted_layer = fmt_try_5
                else:
                    fmt_try_4 = _format_line(list(layer_idx_fmt), [4])
                    formatted_layer = fmt_try_4 if len(fmt_try_4) == 5 else _format_line(list(layer_idx_fmt), [3])

                row = [formatted_layer]
                vals = layer.get("ioa", [])
                for v in vals:
                    row.append(_float_digit(str(v), '1.4f', 1) + '0')
                rows.append(row)
            rows.reverse() 
            ind_aer_output.append(rows)

        # SSA
        if int(ISSA_raw) == 0:
            ib16 = _float_digit(str(aer.get("ssa", "")), '1.2f', 1) + '0'
            ind_aer_output.append([ib16])
        else:
            ind_aer_output.append([_float_digit(str(v), '1.2f', 1) + '0' for v in aer.get("ssa", [])])

        # IPHA
        if int(IPHA_raw) == 0:
            ib16 = _float_digit(str(aer.get("ipha", "")), '1.2f', 1) + '0'
            ind_aer_output.append([ib16])
        else:
            ind_aer_output.append([_float_digit(str(v), '1.2f', 1) + '0' for v in aer.get("ipha", [])])

        output.append(ind_aer_output)

    buf = StringIO()
    for i, item in enumerate(output):
        if i > 0:
            buf.write(''.join(item[0] + item[1]) + '\n')
            for sub in item[2:]:
                if isinstance(sub[0], list):
                    for sub2 in sub:
                        buf.write(''.join(sub2) + '\n')
                else:
                    buf.write(''.join(sub) + '\n')
        elif isinstance(item, list):
            buf.write(''.join(item) + '\n')
        else:
            buf.write(str(item) + '\n')
    return buf.getvalue()

#Form parsing, it canaccept IAOD or IOAD
def parse_form(form):
    try:
        naer = int(form.get("NAER", "1"))
    except ValueError:
        naer = 1

    aerosols = []
    for i in range(naer):
        prefix = f"aerosols-{i}-"
        def g(name, default=""):
            return form.get(prefix + name, default).strip()

        NLAY = g("NLAY", "0")

        IAOD = form.get(prefix + "IAOD", None)
        if IAOD is None:
            IAOD = g("IOAD", "0")
        else:
            IAOD = IAOD.strip()

        ISSA = g("ISSA", "0")
        IPHA = g("IPHA", "0")

        # Layers
        layers = []
        nlay_int = _as_int(NLAY) or 0
        for j in range(nlay_int):
            layer_idx = g(f"layer-{j}-index", "")
            if IAOD == "0":
                ioa_val = g(f"layer-{j}-od", "")
            else:
                ioa_val = []
                for k in range(14):
                    ioa_val.append(g(f"layer-{j}-od-{k}", ""))
            layers.append({"layer": layer_idx, "ioa": ioa_val})

        data = {
            "NLAY": NLAY,
            "IAOD": IAOD,
            "ISSA": ISSA,
            "IPHA": IPHA,
            "layers": layers,
        }

        if IAOD == "0":
            data["AERPAR1"] = g("AERPAR1", "")
            data["AERPAR2"] = g("AERPAR2", "")
            data["AERPAR3"] = g("AERPAR3", "")

        if ISSA == "0":
            data["ssa"] = g("ssa-0", "")
        else:
            ssa_vals = []
            for k in range(14):
                ssa_vals.append(g(f"ssa-{k}", ""))
            data["ssa"] = ssa_vals

        if IPHA == "0":
            data["ipha"] = g("ipha-0", "")
        else:
            ipha_vals = []
            for k in range(14):
                ipha_vals.append(g(f"ipha-{k}", ""))
            data["ipha"] = ipha_vals

        aerosols.append(data)

    return aerosols

#Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("form.html")

@app.route("/generate", methods=["POST"])
def generate():
    aerosols = parse_form(request.form)
    errors = validate_aerosols(aerosols)
    if errors:
        msg = "Input validation failed:\n\n" + "\n".join(f"- {e}" for e in errors)
        return Response(msg, status=400, mimetype="text/plain; charset=utf-8")

    content = build_aer_input(aerosols)
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=Aer_input.txt"},
    )

if __name__ == "__main__":

    app.run(host="127.0.0.1", port=7860, debug=False)


