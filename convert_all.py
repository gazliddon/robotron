import os, glob, re

inherent_mnemonics = {
    "abx", "asla", "aslb", "asra", "asrb", "clra", "clrb", "coma", "comb", "cwai", "daa",
    "deca", "decb", "inca", "incb", "lsra", "lsrb", "mul", "nega", "negb", "nop", "rola",
    "rolb", "rora", "rorb", "rti", "rts", "sex", "swi", "swi2", "swi3", "sync", "tsta", "tstb"
}

mnemonic_aliases = {
    "ldaa": "lda",
    "ldab": "ldb",
    "staa": "sta",
    "stab": "stb",
    "oraa": "ora",
    "orab": "orb",
    "cpx": "cmpx",
    "cmpaa": "cmpa",
    "cmpab": "cmpb",
    "addaa": "adda",
    "subaa": "suba",
}

def clean_operand(op, operand):
    # Fix post-increment 0,X+ -> ,X+ etc.
    operand = re.sub(r"\b0\s*,\s*([xXyYuUsS])\+\+", r",\1++", operand)
    operand = re.sub(r"\b0\s*,\s*([xXyYuUsS])\+", r",\1+", operand)
    operand = re.sub(r"\b0\s*,\s*([xXyYuUsS])\-\-", r",\1--", operand)
    operand = re.sub(r"\b0\s*,\s*([xXyYuUsS])\-", r",\1-", operand)
    return operand

nullary_macros = {"clc", "sec", "cli", "sei", "die"}
macro_names = {"makp", "nap", "sleep", "newp", "mkprob", "kilp", "kilo", "obi", "clrd"}

def convert_file(asm_path, gazm_path):
    fname = os.path.basename(asm_path)
    base_name, _ = os.path.splitext(fname)
    is_rrs22 = (base_name.upper() == "RRS22")
    is_rrf = (base_name.upper() == "RRF")
    is_rrfred = (base_name.upper() == "RRFRED")
    
    with open(asm_path, "r", errors="ignore") as f:
        lines = f.readlines()
        
    out_lines = []
    in_old_macro = False
    in_vector_table = False
    current_org = None
    current_offset = 0
    
    for line in lines:
        raw = line.rstrip("\r\n")
        if not raw.strip():
            out_lines.append("")
            continue
            
        if raw.startswith("*") or raw.startswith(";"):
            out_lines.append(";" + raw[1:] if raw.startswith("*") else raw)
            continue
            
        # Check for macro definition block in RRF
        if re.search(r"\bMACRO\b", raw, re.I):
            in_old_macro = True
            out_lines.append(f"; {raw.strip()}")
            continue
        if in_old_macro:
            out_lines.append(f"; {raw.strip()}")
            if re.search(r"\bENDM\b", raw, re.I):
                in_old_macro = False
            continue
            
        # Ignore conditional assembly directives
        if re.match(r"^\s*(IFC|IFNC|ENDIF|ELSE)\b", raw, re.I):
            out_lines.append(f"; {raw.strip()}")
            continue
            
        # For RRF.ASM: convert dummy ORG ... RMB vector tables (lines 85-271) to equates
        if is_rrf:
            org_match = re.match(r"^\s*([A-Za-z0-9_]+)\s+EQU\s+(\$[0-9A-Fa-f]+|\d+)", raw)
            if org_match and org_match.group(1).endswith("ORG") and org_match.group(1) not in ("SETORG", "TABORG", "TSTORG", "TSBORG", "TXORG", "LOGORG", "TSCORG", "P1ORG", "P2ORG", "DMAORG"):
                current_org = org_match.group(1)
                current_offset = 0
                out_lines.append(f"{current_org}: equ {org_match.group(2)}")
                continue
            if re.match(r"^\s*ORG\s+([A-Za-z0-9_]+)", raw) and current_org:
                continue
            rmb_match = re.match(r"^([A-Za-z0-9_]+)\s+RMB\s+(\d+)", raw)
            if rmb_match and current_org:
                sym = rmb_match.group(1)
                size = int(rmb_match.group(2))
                out_lines.append(f"{sym + ':':<16}equ {current_org} + {current_offset}")
                current_offset += size
                continue
            if re.match(r"^\s*RMB\s+15\*\(120\)", raw, re.I):
                out_lines.append("                rmb      15*120")
                continue
            if re.match(r"^\s*RMB\s+\(180\)\*OSIZE", raw, re.I):
                out_lines.append("                rmb      180*OSIZE")
                continue
            if current_org and (re.match(r"^\s*ORG\s+\$9800", raw) or re.match(r"^\s*LOGORG\b", raw)):
                current_org = None
                
        # For RRFRED: comment out LIB RRF and replace HXTAB RMBs with equates
        if is_rrfred:
            if re.match(r"^\s*LIB\s+RRF\b", raw, re.I):
                out_lines.append(f"; {raw.strip()} ; (included globally in robotron.gazm)")
                continue
            if re.match(r"^\s*ORG\s+HXTAB", raw, re.I):
                out_lines.append("; ORG HXTAB")
                out_lines.append("EGRAM:          equ HXTAB")
                out_lines.append("EGRAM2:         equ HXTAB + 2")
                out_lines.append("PLRX:           equ HXTAB + 4")
                out_lines.append("ALTBL:          equ HXTAB + 6")
                continue
            if re.match(r"^\s*(EGRAM|EGRAM2|PLRX|ALTBL)\s+RMB", raw, re.I):
                continue
            if re.match(r"^\s*ORG\s+ALTBL\+60", raw, re.I):
                out_lines.append("; ORG ALTBL+60")
                out_lines.append("ARAM1:          equ ALTBL + 60")
                out_lines.append("ERLIST:         equ ARAM1 + 392")
                out_lines.append("EREND:          equ ERLIST + 28*2")
                continue
            if re.match(r"^\s*(ARAM1|ERLIST)\s+RMB", raw, re.I) or re.match(r"^\s*EREND\s+EQU", raw, re.I):
                continue
                
        # In other files, ignore redundant LIB RRF / LIB RRFRED
        if not is_rrf and not is_rrfred:
            if re.match(r"^\s*LIB\s+(RRF|RRFRED)\b", raw, re.I):
                out_lines.append(f"; {raw.strip()} ; (included globally in robotron.gazm)")
                continue
                
        # In RRX7, map YSIZE: EQU HXRAM to equ $98A1
        if base_name.upper() == "RRX7" and re.match(r"^\s*YSIZE\s+EQU\s+HXRAM", raw, re.I):
            out_lines.append("YSIZE:          equ $98A1")
            continue
            
        # In RRLOG, avoid duplicate include of RRSCRIPT from IFC/ELSE
        if base_name.upper() == "RRLOG" and "RRSCRIPT" in raw:
            if any("RRSCRIPT" in o for o in out_lines):
                out_lines.append(f"; {raw.strip()} ; (duplicate include removed)")
                continue
                
        # In RRTEXT, remove the duplicate WORDZ: EQU * from the ELSE branch
        if base_name.upper() == "RRTEXT" and re.match(r"^\s*WORDZ\s+EQU\b", raw, re.I):
            out_lines.append(f"; {raw.strip()} ; (disabled ELSE branch of IFNC)")
            continue
            
        # In RRCHRIS, comment out duplicate KLJMP
        if base_name.upper() == "RRCHRIS" and re.match(r"^\s*KLJMP\s+EQU\b", raw, re.I):
            out_lines.append(f"; {raw.strip()} ; (defined in RRDX2)")
            continue
            
        # In RRCHRIS, comment out duplicate DXRAM RMBs
        if base_name.upper() == "RRCHRIS" and re.match(r"^\s*(ORG\s+DXRAM|YYCNT|YOFF|XSIZE|YSIZE|EXPTR|APPTR|EXFREE|HITE|TEMP1|TEMP2)\b", raw):
            out_lines.append(f"; {raw.strip()} ; (declared in RRDX2)")
            continue
            
        # In RRH11, line 1194 remove duplicate BRLP1 label on HLKLP1
        if base_name.upper() == "RRH11" and raw.startswith("BRLP1"):
            raw = raw.replace("BRLP1", "     ")
            
        # In RRDX2, rename local GETBLK -> GETBLK_DX, PICPTR -> PICPTR_DX, DATA -> DATA_DX
        if base_name.upper() == "RRDX2":
            raw = re.sub(r"\bGETBLK\b", "GETBLK_DX", raw)
            raw = re.sub(r"\bPICPTR\b", "PICPTR_DX", raw)
            raw = re.sub(r"\bDATA\b", "DATA_DX", raw)
            
        # In RRHX4, rename local GETBLK -> GETBLK_HX
        if base_name.upper() == "RRHX4":
            raw = re.sub(r"\bGETBLK\b", "GETBLK_HX", raw)
            
        # In RRT2, rename local GETBLK -> GETBLK_T2
        if base_name.upper() == "RRT2":
            raw = re.sub(r"\bGETBLK\b", "GETBLK_T2", raw)
            
        converted = convert_line(raw)
        
        # Rename EXEC -> EXEC_LOOP in RRS22
        if is_rrs22:
            converted = re.sub(r"\bEXEC\b", "EXEC_LOOP", converted)
            
        out_lines.append(converted)
        
    with open(gazm_path, "w") as f:
        f.write("\n".join(out_lines) + "\n")

def convert_line(line):
    raw = line.rstrip("\r\n")
    if not raw.strip():
        return ""
    if raw.startswith("*") or raw.startswith(";"):
        return ";" + raw[1:] if raw.startswith("*") else raw
        
    semicolon_comment = ""
    if ";" in raw:
        idx = raw.find(";")
        semicolon_comment = raw[idx:]
        raw = raw[:idx]
        
    # Check for LIB EQU
    lib_equ_match = re.match(r"^\s*LIB\s+(EQU|equ)\s+(.*)$", raw)
    if lib_equ_match:
        val = lib_equ_match.group(2).strip()
        return f"LIB:            equ {val}{semicolon_comment}"
        
    # Replace LIB filename
    lib_match = re.match(r"^\s*LIB\s+([A-Za-z0-9_]+)\b(.*)$", raw, re.I)
    if lib_match:
        inc = lib_match.group(1)
        comment = lib_match.group(2).strip()
        c_str = f" ; {comment}" if comment else ""
        return f"                include \"{inc}.gazm\"{c_str}{semicolon_comment}"
        
    opt_match = re.match(r"^\s*(OPT|TTL|STTL|PAGE|PAG|PAGS|IFNC|ELSE|ENDIF|END)\b(.*)$", raw, re.I)
    if opt_match and not (opt_match.group(1).upper() == "OPT" and re.match(r"^\s*EQU\b", opt_match.group(2), re.I)):
        return f"; {raw.strip()}{semicolon_comment}"
        
    label = ""
    rest = raw
    if raw[0] not in (" ", "\t"):
        parts = re.split(r"(\s+)", raw, maxsplit=1)
        label = parts[0]
        rest = parts[1] + parts[2] if len(parts) > 2 else ""
        if not label.endswith(":"):
            label = label + ":"
            
    rest_trimmed = rest.strip()
    if not rest_trimmed:
        return label + semicolon_comment
        
    parts = re.split(r"\s+", rest_trimmed, maxsplit=1)
    op = parts[0]
    tail = parts[1] if len(parts) > 1 else ""
    
    op_lower = op.lower()
    
    # Handle nullary macros
    if op_lower in nullary_macros:
        comment = f" ; {tail}" if tail else ""
        return f"{label:<16}{op_lower}(){comment}{semicolon_comment}".rstrip()
        
    # Handle parameterized macros
    if op_lower in macro_names:
        if tail:
            tail_trimmed = tail.strip()
            # Split operand and comment
            split_pos = len(tail_trimmed)
            for i, ch in enumerate(tail_trimmed):
                if ch in (" ", "\t"):
                    split_pos = i
                    break
            operand = tail_trimmed[:split_pos]
            comment = tail_trimmed[split_pos:].strip()
            c_str = f" ; {comment}" if comment else ""
            clean_op_val = clean_operand(op, operand)
            return f"{label:<16}{op_lower}({clean_op_val}){c_str}{semicolon_comment}".rstrip()
        else:
            return f"{label:<16}{op_lower}(){semicolon_comment}".rstrip()
            
    # Normalize op aliases
    if op_lower in mnemonic_aliases:
        op = mnemonic_aliases[op_lower]
        op_lower = op.lower()
        
    if op_lower in inherent_mnemonics:
        comment = f" ; {tail}" if tail else ""
        return f"{label:<16}{op}{comment}{semicolon_comment}".rstrip()
        
    if op_lower == "fcc":
        tail_trimmed = tail.strip()
        if tail_trimmed:
            delim = tail_trimmed[0]
            if delim in ("/", "\\", "\"", "\x27", "!"):
                end_idx = tail_trimmed.find(delim, 1)
                if end_idx != -1:
                    str_content = tail_trimmed[1:end_idx]
                    comment_text = tail_trimmed[end_idx+1:].strip()
                    c_str = f" ; {comment_text}" if comment_text else ""
                    if "\"" in str_content:
                        byte_strs = [str(ord(c)) for c in str_content]
                        return f"{label:<16}fcb      {','.join(byte_strs)}{c_str}{semicolon_comment}".rstrip()
                    else:
                        return f"{label:<16}fcc \"{str_content}\"{c_str}{semicolon_comment}".rstrip()
            elif "," in tail_trimmed:
                m = re.match(r"^(\d+\s*,\s*[^ \t]+)(.*)$", tail_trimmed)
                if m:
                    operand = m.group(1)
                    comment = m.group(2).strip()
                    c_str = f" ; {comment}" if comment else ""
                    return f"{label:<16}{op} {operand}{c_str}{semicolon_comment}".rstrip()
                    
    if tail:
        tail_trimmed = tail.strip()
        in_quote = False
        quote_char = None
        bracket_depth = 0
        split_pos = len(tail_trimmed)
        
        for i, ch in enumerate(tail_trimmed):
            if in_quote:
                if ch == quote_char:
                    in_quote = False
            elif ch in ("\"", "\x27"):
                in_quote = True
                quote_char = ch
            elif ch in ("[", "("):
                bracket_depth += 1
            elif ch in ("]", ")"):
                bracket_depth = max(0, bracket_depth - 1)
            elif ch in (" ", "\t") and bracket_depth == 0:
                split_pos = i
                break
                
        operand = tail_trimmed[:split_pos]
        comment = tail_trimmed[split_pos:].strip()
        c_str = f" ; {comment}" if comment else ""
        clean_op_val = clean_operand(op, operand)
        return f"{label:<16}{op:<8} {clean_op_val}{c_str}{semicolon_comment}".rstrip()
    else:
        return f"{label:<16}{op}{semicolon_comment}".rstrip()

src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
orig_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig", "src")
asm_files = glob.glob(os.path.join(orig_dir, "*.ASM"))

for asm_path in sorted(asm_files):
    fname = os.path.basename(asm_path)
    base_name, _ = os.path.splitext(fname)
    gazm_path = os.path.join(src_dir, f"{base_name}.gazm")
    convert_file(asm_path, gazm_path)
        
print("Reconverted", len(asm_files), "files.")
