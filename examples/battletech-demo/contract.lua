-- Query flags; payments and continuations remain ordinary saved commands.
if game.flag("beacon:relay-clear") then
  return game.command("beacon:relay-report")
elseif game.flag("beacon:paid-road") then
  return game.command("beacon:second-offer")
elseif game.flag("beacon:road-clear") then
  return game.command("beacon:road-report")
elseif game.flag("beacon:accepted") then
  return game.command("beacon:reminder")
else
  return game.command("beacon:offer")
end
