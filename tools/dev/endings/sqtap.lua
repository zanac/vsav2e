-- logs the 68000's state when it writes an effect number (0xe4-0xe8) to the QSound shared RAM
local cpu=manager.machine.devices[':maincpu']
local sp=cpu.spaces['program']
local active=false local log={}
sqtap=sp:install_write_tap(0xff0e0e,0xff1e0d,'sq',function(offset,data,mask)
  if active and #log<3000 then
    local s=string.format('%x pc=%x d=%x m=%x a7=%x r=%x',offset,cpu.state['CURPC'].value,data,mask,cpu.state['A7'].value,sp:read_u32(cpu.state['A7'].value))
    for _,r in ipairs({'D0','D1','D2','A0','A1','A2','A3','A4','A5','A6'}) do s=s..string.format(' %s=%x',r,cpu.state[r].value) end
    log[#log+1]=s
  end
  return data end)
local done=false
function on_frame2(f)
  local mode=sp:read_u16(0xff8004)
  if mode==0x0a and not active and not done then active=true end
  if active and mode~=0x0a then
    done=true; active=false
    local fh=io.open(os.getenv('TRACE_OUT')..'/sq.txt','w'); for _,l in ipairs(log) do fh:write(l..'\n') end; fh:close()
    manager.machine:exit()
  end
end
local fh=io.open("/tmp/claude-0/vs/lua/drive.lua"); local src=fh:read("a"); fh:close(); load(src,"drive","t",_ENV)()
