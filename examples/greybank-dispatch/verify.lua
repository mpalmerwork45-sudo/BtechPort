-- Queries are immutable; the engine commits the declared continuation.
if game.variable("recovery:data") == 2 and game.variable("recovery:surveyed")
   and game.objective("recovery:extract") == "active"
   and game.in_region("recovery:landing-pad") then
    return game.command("recovery:extract-complete")
end
return game.command("recovery:error")
