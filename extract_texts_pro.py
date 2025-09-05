from ida_domain import Database
from ida_domain.operands import OperandType
from tqdm import tqdm
from ida_domain.base import InvalidEAError
from constants import *

 
def extract(db_path):
    with Database.open(path=db_path, save_on_close=False) as db:
        mappings = db.functions.get_at(PLOT_MAPPINGS_ADDR)
        print('name: ' + mappings.name)
        mappings_instructions = list(db.functions.get_instructions(mappings))
        print('total instructions: ' + str(len(mappings_instructions)))
        total_valid = 0
        
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
                instructions = list(db.functions.get_instructions(func))

                for j, instruction in enumerate(instructions):
                    print(db.instructions.get_operands(instruction))
                    print(db.instructions.get_disassembly(instruction))
                    opr = db.instructions.get_operand(instruction, 0)
                    if opr is None: continue
                    if opr.get_value() == PLAY_DIALOG_ADDR:  # PlayDialog (0x41E530)
                        # content = extract_dialog_text(db, instructions, j)
                        # print('PlayDialog: ' + content)
                        valid += 1
                        total_valid += 1
                tqdm.write(f'Found {valid} texts.')
                break
            except InvalidEAError as e: continue
            except Exception as e:
                tqdm.write('Unhandled Error: ' + str(e))
                continue

        tqdm.write(f'Total valid texts: {total_valid}')
    tqdm.write('✓ Database closed')


if __name__ == '__main__':
    extract("./alive.exe.i64")