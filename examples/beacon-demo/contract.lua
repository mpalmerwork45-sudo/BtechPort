-- Pure queries select shared, saved commands. No Lua stack is saved.
if game.flag("beacon:paid") then
  return game.command("beacon:completed")
elseif game.flag("beacon:cleared") and game.flag("beacon:hired") then
  return game.command("beacon:reward")
elseif game.flag("beacon:hired") then
  return game.command("beacon:reminder")
else
  return game.command("beacon:offer")
end
