#!/usr/bin/env python3
import re
import sys
import os

def fix_dollar(text):
    # A hex literal is ($[0-9A-Fa-f]+)
    def sub_fn(m):
        tok = m.group(0)
        if re.match(r"^\$[0-9A-Fa-f]+$", tok):
            return tok
        return tok.replace("$", "_")
        
    return re.sub(r"[\$A-Za-z0-9_]+", sub_fn, text)

def parse_tail(tail):
    tokens = tail.split()
    if not tokens:
        return "", ""
        
    # Special case: standalone * (current PC, e.g. "BRA *", "BEQ * NOPE")
    if tokens[0] == "*":
        return "*", " ".join(tokens[1:])
        
    operand_tokens = []
    comment_tokens = []
    in_operand = True
    operators = {"+", "-", "/", "&", "|", "^", ">>", "<<", "="}
    
    for idx, tok in enumerate(tokens):
        if in_operand:
            if tok.startswith("-I"):
                in_operand = False
                comment_tokens.append(tok)
                continue
                
            operand_tokens.append(tok)
            if tok in operators or tok.endswith(("+", "-", "*", "/", "&", "|", "^", ">>", "<<", ",")):
                continue
            if idx + 1 < len(tokens):
                next_tok = tokens[idx + 1]
                if next_tok.startswith("-I"):
                    in_operand = False
                    continue
                if next_tok in operators or next_tok.startswith(("+", "-", "*", "/", "&", "|", "^", ">>", "<<", ",")):
                    continue
            in_operand = False
        else:
            comment_tokens.append(tok)
            
    return " ".join(operand_tokens), " ".join(comment_tokens)

def convert_sound_file(src_path, dst_path):
    with open(src_path, "r", encoding="latin-1") as f:
        lines = f.readlines()
        
    out_lines = []
    
    inherent_6800 = {
        "sei", "cli", "clra", "clrb", "dex", "inx", "des", "ins",
        "wai", "rts", "rti", "coma", "comb", "asla", "aslb", "lsra", "lsrb",
        "rora", "rorb", "rola", "rolb", "deca", "decb", "inca", "incb",
        "tsta", "tstb", "tab", "tba", "txs", "tsx", "daa", "aba", "cba",
        "sba", "nop", "sec", "clc", "sev", "clv", "winc", "psha", "pshb",
        "pula", "pulb", "nega", "negb"
    }
    
    for line in lines:
        raw = line.rstrip("\r\n")
        if not raw.strip():
            out_lines.append("")
            continue
            
        if raw.startswith("*") or raw.startswith(";"):
            out_lines.append(";" + raw[1:] if raw.startswith("*") else raw)
            continue
            
        # Replace tabs with spaces
        raw = raw.replace("\t", " ")
        
        semicolon_comment = ""
        if ";" in raw:
            idx = raw.find(";")
            semicolon_comment = raw[idx:]
            raw = raw[:idx]
            
        # Ignore NOGEN / NAM / END (directive at indentation)
        if re.match(r"^\s+(NOGEN|NAM|END)\b", raw, re.I) or re.match(r"^(NOGEN|NAM)\b", raw, re.I):
            out_lines.append(f"; {raw.strip()}{semicolon_comment}")
            continue
            
        # Replace !> with >> (e.g. 34715!>1 -> 34715 >> 1)
        raw = raw.replace("!>", " >> ")
        
        # Replace !. with & (e.g. SINTBL!.$FF -> SINTBL & $FF)
        raw = raw.replace("!.", " & ")
        
        # Replace GS1.7 with GS1_7
        raw = re.sub(r"\bGS1\.7\b", "GS1_7", raw)
        
        # Replace $ in identifiers (not hex literals)
        raw = fix_dollar(raw)
        
        # Parse label vs opcode depending on leading whitespace
        if raw[0] == " ":
            label = ""
            m = re.match(r"^\s+([A-Za-z0-9_]+)(?:\s+(.*))?$", raw)
            if not m:
                out_lines.append(raw + semicolon_comment)
                continue
            op = m.group(1) or ""
            tail = m.group(2) or ""
        else:
            m = re.match(r"^([A-Za-z0-9_!]+)(?:\s+([A-Za-z0-9_]+))?(?:\s+(.*))?$", raw)
            if not m:
                out_lines.append(raw + semicolon_comment)
                continue
            label = m.group(1) or ""
            op = m.group(2) or ""
            tail = m.group(3) or ""
            if label:
                label = label + ":"
        
        if not op:
            out_lines.append(f"{label}{semicolon_comment}".rstrip())
            continue
            
        op_lower = op.lower()
        
        # If EQU * -> turn into just label:
        if op_lower == "equ" and tail.strip().startswith("*"):
            rem_comment = tail.strip()[1:].strip()
            c_str = f" ; {rem_comment}" if rem_comment else ""
            out_lines.append(f"{label}{c_str}{semicolon_comment}".rstrip())
            continue
            
        # Convert shorthand "LDAA X" -> "LDAA 0,X"
        if tail.strip() == "X" or tail.strip().startswith("X "):
            tail = "0,X" + tail.strip()[1:]
            
        if op_lower in inherent_6800:
            comment = f" ; {tail}" if tail else ""
            out_lines.append(f"{label:<16}{op_lower}{comment}{semicolon_comment}".rstrip())
            continue
            
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
                        out_lines.append(f"{label:<16}fcc \"{str_content}\"{c_str}{semicolon_comment}".rstrip())
                        continue
                        
        if tail:
            tail_trimmed = tail.strip()
            operand_str, comment_str = parse_tail(tail_trimmed)
            # Add spaces around '-' in expressions if not already spaced
            operand_str = re.sub(r"([A-Za-z0-9_]+)-([A-Za-z0-9_]+)", r"\1 - \2", operand_str)
            c_str = f" ; {comment_str}" if comment_str else ""
            out_lines.append(f"{label:<16}{op:<8} {operand_str}{c_str}{semicolon_comment}".rstrip())
        else:
            out_lines.append(f"{label:<16}{op}{semicolon_comment}".rstrip())
            
    with open(dst_path, "w") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"Converted {src_path} -> {dst_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(base_dir, "orig", "src", "VSNDRM3.SRC")
    dst = os.path.join(base_dir, "snd_src", "vsndrm3.src")
    convert_sound_file(src, dst)
