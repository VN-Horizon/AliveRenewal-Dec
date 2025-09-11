from ida_domain.operands import OperandType
from ida_domain.operands import AccessType
from tqdm import tqdm
from constants import *
from typing import List
import math

class EventMapping:
    def __init__(self, flag0: int, evId: int, flag1: int, voiceKey: str, evFunc: str, valueName: str, address: int, pos: int):
        self.flag0 = flag0
        self.evId = int(evId) + 1
        self.flag1 = flag1
        self.voiceKey = str(voiceKey).replace('(int)', '')
        self.valueName = str(valueName).replace('(int)', '')
        self.evFunc = evFunc
        self.address = address
        self.pos = pos
        self.instructions = []
        self.return_values = []
        self.has_choices = False
    
    def get_instructions(self, db):
        if self.evFunc in ['0', 0]: return
        tqdm.write(f'getting instructions for {self.evFunc}...')
        
        # Or get the raw data for further processing
        self.extract_function_calls(db)
    
    def extract_function_calls(self, db):
        """Extract function calls from IsCurrentLine branches using raw opcodes and operands"""
        if isinstance(self.evFunc, int):
            func_name = db.functions.get_at(self.evFunc).name
        else:
            func_name = self.evFunc.replace('(int)', '')
        
        try:
            func = db.functions.get_function_by_name(func_name)
            if not func:
                tqdm.write(f"Function {func_name} not found")
                return []
            
            if func.start_ea in exclude_subs or func.start_ea > 0x64c800:
                tqdm.write(f"Function {func_name} is in exclude_subs or > 0x64c800")
                return []

            instructions = list(db.functions.get_instructions(func))

            for i in range(len(instructions)):
                inst = instructions[i]
                
                # Check if this is a call instruction using opcode
                if db.instructions.is_call_instruction(inst):
                    func = db.instructions.get_operand(inst, 0)
                    f_name = func.get_name()
                    if f_name in exclude_calls: continue
                    func_addr = func.get_value()
                    if func_addr == IS_CURRENT_LINE_ADDR:
                        calls = self._extract_line_parameter(db, instructions, i)
                        if calls is not None: current_line_index = calls
                    else:
                        params = self._extract_parameters(db, instructions, i)

                        if func_addr in [PLAY_DIALOG_ADDR, PLAY_BGM_ADDR, PLAY_SE_ADDR, SHOW_CG_ADDR,
                        GET_TICK_COUNT_ADDR]:
                            params[0] = self._get_string_data(db, params[0])
                            if func_addr == PLAY_DIALOG_ADDR and len(params) >= 3:
                                params[2] = (params[2] & 0xFF)
                                if params[2] > 0x7F:
                                    params[2] = params[2] - 0x100
                        
                        elif func_addr in [SET_BG_IMG_ADDR, SET_CHARA_IMG_ADDR]:
                            params[0] = self._get_string_data(db, params[0])
                            params[1] = self._get_string_data(db, params[1])
                        
                        elif func_addr in [TRANSITION_TO_GRAPHICS_ADDR, TRANSITION_TO_GRAPHICS_FADE_ADDR]:
                            params[0] = self._get_string_data(db, params[0])
                            params[1] = self._get_string_data(db, params[1])
                            params[2] = self._get_string_data(db, params[2])
                            params[3] = self._get_string_data(db, params[3])
                            
                        elif func_addr in [SLEEP_OR_FADE_ADDR, FADE_SYSTEM_TO_BLACK_ADDR, 
                        SET_GRAPHICS_STATE_ADDR, TOGGLE_GRAPHICS_FLAG_ADDR, SHAKE_SCREEN_ADDR,
                        TOGGLE_STAFF_STATE, SHOW_STAFF_A_ADDR, SHOW_STAFF_B_ADDR]: pass
                    
                        elif func_addr == SHOW_DECISION_ADDR:
                            params = [self._get_string_data(db, param) for param in params]
                            tqdm.write(f'Decision branch founded at: {current_line_index}')
                            tqdm.write(f'Decisions: {params}')
                            ret = self._get_choices_return(db, instructions, i)
                            tqdm.write(f'Choices return: {ret}')
                            self.return_values = ret
                            self.has_choices = True
                        else:
                            params = [self._get_string_data(db, param) for param in params]
                            tqdm.write(f'warning: unknown function: {f_name}: {params}')

                        self.instructions.append({'name': f_name, 'params': params})
            
            if not self.has_choices:
                retn = self._get_direct_return(db, instructions)
                tqdm.write(f'Direct return: {retn}')
                self.return_values = [retn]
            
        except Exception as e:
            tqdm.write(f"Error extracting function calls: {e}")
            return []

    def to_dict(self):
        d = self.__dict__
        del d['evFunc']
        del d['valueName']
        return d

    def _extract_line_parameter(self, db, instructions, call_index):
        inst = db.instructions.get_operand(instructions[call_index-2], 0)
        if inst.type != OperandType.IMMEDIATE:
            tqdm.write("--------------------------------")
            tqdm.write(f"get line parameter error: {inst.type} is not an immediate value")
            disasm = db.instructions.get_disassembly(inst)
            tqdm.write(disasm)
            tqdm.write(db.instructions.get_operands(inst))
            tqdm.write("--------------------------------")
            return None
        return inst.get_value()

    def _extract_parameters(self, db, instructions, call_index):
        has_push = False
        for i in range(call_index - 1, call_index - 8, -1):
            inst = instructions[i]
            operand = db.instructions.get_operand(inst, 0)
            if operand.type == OperandType.IMMEDIATE:
                has_push = True
                break
        if not has_push:
            tqdm.write("--------------------------------")
            tqdm.write(f"extract parameters error: no push instruction before")
            tqdm.write(instructions[call_index])
            tqdm.write("--------------------------------")
            return None
        params = []
        for i in range(i, i - 20, -1):
            inst = instructions[i]
            if db.instructions.is_indirect_jump_or_call(inst): break
            operand = db.instructions.get_operand(inst, 0)
            if operand.type != OperandType.IMMEDIATE: break
            params.append(operand.get_value())
        return params

    def _get_direct_return(self, db, instructions):
        for i in range(-1, -8, -1):
            inst = instructions[i]
            if db.instructions.is_indirect_jump_or_call(inst): continue
            operand = db.instructions.get_operands(inst)
            if len(operand) == 0 or operand[0] is None: continue
            # push or mov eax, val
            if operand[0].type == OperandType.IMMEDIATE:
                return operand[0].get_value()
            elif len(operand) == 2 and operand[0].type == OperandType.REGISTER and operand[0].get_register_name() == 'eax' and operand[0].get_access_type() == AccessType.WRITE and operand[1].type == OperandType.IMMEDIATE:
                return operand[1].get_value()
        return None

    def _get_string_data(self, db, addr):
        if addr < DATA_BOUNDARY[0] or addr > DATA_BOUNDARY[1]:
            return addr
        data = []
        ptr = addr
        try:
            for i in range(1024):
                byte_val = db.bytes.get_byte_at(ptr)
                if byte_val == 0: break
                data.append(byte_val)
                ptr += 1
            return bytes(data).decode('shift-jis', errors='replace')
        except Exception as e:
            tqdm.write(f"Error getting string data: {e}")
            return addr

    def _get_choices_return(self, db, instructions, call_index):
        ret = []
        for i in range(call_index + 7, instructions.__len__()):
            inst = instructions[i]
            if db.instructions.is_indirect_jump_or_call(inst): continue
            operand = db.instructions.get_operands(inst)
            if len(operand) == 0 or operand[0] is None: continue
            # push or mov eax, val
            if operand[0].type == OperandType.IMMEDIATE:
                ret.append(operand[0].get_value())
            elif len(operand) == 2 and operand[0].type == OperandType.REGISTER and operand[0].get_register_name() == 'eax' and operand[0].get_access_type() == AccessType.WRITE and operand[1].type == OperandType.IMMEDIATE:
                ret.append(operand[1].get_value())
        
        # Clamp to exactly 3 items, add 0 if less
        while len(ret) < 3:
            ret.append(0)
        return ret[:3]
    
    def __str__(self):
        return f"EventMapping(flag0={self.flag0}, evId={self.evId}, flag1={self.flag1}, voiceKey={self.voiceKey}, valueName={self.valueName}, evFunc={self.evFunc}, address={self.address}, pos={self.pos})"

def get_event_mappings(pseudocode: List[str]):
    event_mappings = []
    map_dict = {}
    
    # First pass: collect all values by position and index
    for line in pseudocode[4:-2]:
        addr, val = line.rstrip(";").replace(' ', '').split('=')
        if addr == 'result': continue
        addr = int(addr.replace('dword_', ''), 16)
        ind = int((addr / 4 + 5) % 6)
        pos = int(math.floor((addr - 7783996) / 24))
        
        # Group by position
        if pos not in map_dict:
            map_dict[pos] = {}
        map_dict[pos][ind] = val
    
    # Second pass: create EventMapping objects
    for pos, values in map_dict.items():
        # Create EventMapping with values in correct order: flag0, evId, flag1, voiceKey, valueName, evFunc
        event_mapping = EventMapping(
            flag0=values.get(0, 0),
            evId=values.get(1, 0),
            flag1=values.get(2, 0),
            voiceKey=values.get(3, 0),
            valueName=values.get(4, 0),
            evFunc=values.get(5, 0),
            address=7783996 + pos * 24,  # Calculate base address for this position
            pos=pos
        )
        event_mappings.append(event_mapping)
    
    return event_mappings
