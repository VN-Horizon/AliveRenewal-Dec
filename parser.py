from ida_domain.operands import OperandType
from tqdm import tqdm
from constants import *

def extract_dialog_text(db, instructions, j):
    setTextInst = instructions[j-2]
    textOpr = db.instructions.get_operand(setTextInst, 0)
    if textOpr is None: 
        tqdm.write("Error: textOpr is None")
        return None
    if textOpr.type != OperandType.IMMEDIATE:
        tqdm.write("Error: textOpr is not an immediate operand")
        return None

    textAddr = textOpr.get_value()
    if not db.is_valid_ea(textAddr):
        tqdm.write("Error: textOpr is not a valid address")
        return None
    data = []
    ptr = textAddr
    for i in range(1024):
        byte_val = db.bytes.get_byte_at(ptr)
        if byte_val == 0:  # Null terminator
            break
        data.append(byte_val)
        ptr += 1
    content = bytes(data).decode('shift-jis', errors='replace')
    
    # Handle empty line characters and clean content
    return content.strip()
