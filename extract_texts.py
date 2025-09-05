from ida_domain import Database
from ida_domain.operands import OperandType
from tqdm import tqdm
from ida_domain.base import InvalidEAError
from openpyxl import Workbook
from openpyxl.styles import Font
from parser import extract_dialog_text
from constants import *
import os

existing_lines = []
 
def extract(db_path):
    with Database.open(path=db_path, save_on_close=False) as db:
        mappings = db.functions.get_at(PLOT_MAPPINGS_ADDR)
        print('name: ' + mappings.name)
        mappings_instructions = list(db.functions.get_instructions(mappings))
        print('total instructions: ' + str(len(mappings_instructions)))
        total_valid = 0
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Extracted Texts"
        ws.append(['Address', 'Character', 'Content', 'Translation'])
        
        header_font = Font(bold=True)
        for cell in ws[1]:
            cell.font = header_font
        # Add progress bar for main instruction loop
        for i, instruction in tqdm(enumerate(db.functions.get_instructions(mappings)), 
                                 total=len(mappings_instructions), 
                                 desc="Processing mappings instructions"):
            opr = db.instructions.get_operands(instruction)
            if len(opr) < 2: continue
            opr1 = opr[1]
            if opr1 is None or opr1.type != OperandType.IMMEDIATE: continue
            try:
                addr = opr1.get_value()
                func = db.functions.get_at(addr)
                if func is None or func.start_ea in exclude_subs: continue
                
                tqdm.write(f'Reading {i}: {func.name}....', end='')
                valid = 0
                rows = []
                instructions = list(db.functions.get_instructions(func))

                for j, instruction in enumerate(instructions):
                    opr = db.instructions.get_operand(instruction, 0)
                    if opr is None: continue
                    if opr.get_value() == PLAY_DIALOG_ADDR:  # PlayDialog (0x41E530)
                        content = extract_dialog_text(db, instructions, j)
                        
                        # Handle empty line characters and clean content
                        content = content.strip()
                        if not content:
                            continue

                        textAddr = opr.get_value()
                        
                        if content in existing_lines: continue
                        existing_lines.append(content)
                        rows.append([hex(textAddr), '', content, ''])
                        valid += 1
                        total_valid += 1
                tqdm.write(f'Found {valid} texts.')
                if valid > 0:
                    ws.append([hex(func.start_ea), func.name])
                    ws.append([])
                    for row in rows:
                        if row[2][-1] == '」':
                            row[1] = row[2].split('「')[0]
                            row[2] = row[2].split('「')[1].rstrip('」')
                        ws.append(row)
                    ws.append([])
            except InvalidEAError as e: continue
            except Exception as e:
                tqdm.write('Unhandled Error: ' + str(e))
                continue

        tqdm.write(f'Total valid texts: {total_valid}')
        ws.column_dimensions['A'].width = 10
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 100
        ws.column_dimensions['D'].width = 50
        wb.save('texts.xlsx')
        tqdm.write('✓ Excel file saved as texts.xlsx')
        os.startfile('texts.xlsx')
    tqdm.write('✓ Database closed')


if __name__ == '__main__':
    extract("./game/alive.exe.i64")