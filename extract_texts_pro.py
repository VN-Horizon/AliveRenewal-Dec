from ida_domain import Database
from ida_domain.operands import OperandType
from tqdm import tqdm
from ida_domain.base import InvalidEAError
from constants import *
from parser import get_event_mappings

 
def extract(db_path):
    with Database.open(path=db_path, save_on_close=False) as db:
        mappings = db.functions.get_at(PLOT_MAPPINGS_ADDR)
        print('name: ' + mappings.name)
        mappings_instructions = list(db.functions.get_instructions(mappings))
        print('total instructions: ' + str(len(mappings_instructions)))
        print('fetching event metadata...')
        event_mappings = get_event_mappings(db.functions.get_pseudocode(mappings))
        print(f'✓ gathered {len(event_mappings)} event metadata')

        for mapping in event_mappings[:]:
            mapping.get_instructions(db)

    tqdm.write('✓ Database closed')


if __name__ == '__main__':
    extract("./alive.exe.i64")