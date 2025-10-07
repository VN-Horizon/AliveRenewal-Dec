from ida_domain import Database
from tqdm import tqdm
import json
from constants import *
from parser import get_event_mappings, string_pool
from event_mapping_pb2 import EventMappings, EventMapping as PBEventMapping, Instruction
import msgpack
 
def extract(db_path):
    with Database.open(path=db_path, save_on_close=False) as db:
        mappings = db.functions.get_at(PLOT_MAPPINGS_ADDR)
        print('name: ' + mappings.name)
        mappings_instructions = list(db.functions.get_instructions(mappings))
        print('total instructions: ' + str(len(mappings_instructions)))
        print('fetching event metadata...')
        event_mappings = get_event_mappings(db.functions.get_pseudocode(mappings))
        print(f'✓ gathered {len(event_mappings)} event metadata')

        events = []
        for mapping in tqdm(event_mappings[:], desc='Processing events'):
            mapping.get_instructions(db)
            tqdm.write(f'Fetched Event {mapping.evId} instructions: {len(mapping.instructions)}')
            if mapping.evId == 1 and len(mapping.instructions) == 0 and len(mapping.return_values) == 1 and mapping.return_values[0] == 950: continue
            if len(mapping.return_values) == 0: continue
            events.append(mapping)

        print("Got events", len(events))
        events = sorted(events, key=lambda x: x.evId)

        # Create protobuf EventMappings container
        event_mappings_pb = EventMappings()
        event_mappings_pb.text_pool.extend(string_pool)

        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump({'text_pool': string_pool, 'events': [mapping.to_dict() for mapping in events]}, f, ensure_ascii=False)

        with open('events.indent.json', 'w', encoding='utf-8') as f:
            json.dump({'text_pool': string_pool, 'events': [mapping.to_dict() for mapping in events]}, f, ensure_ascii=False, indent=4)

        with open('events.msgpack', 'wb') as f:
            f.write(msgpack.packb({'text_pool': string_pool, 'events': [mapping.to_dict() for mapping in events]}))
        
        for mapping in events:
            # Convert EventMapping to protobuf using the new method
            pb_mapping = mapping.to_protobuf()
            event_mappings_pb.events.append(pb_mapping)

        # Save as protobuf binary format
        with open('events.pb', 'wb') as f:
            f.write(event_mappings_pb.SerializeToString())

    tqdm.write('✓ Database closed')


if __name__ == '__main__':
    extract("./alive.exe.i64")