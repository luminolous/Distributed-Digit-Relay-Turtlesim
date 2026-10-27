# Turn token passed between member nodes over the /relay/turn topic.

int32 current_number    # number to draw now (1..14)
int32 active_member     # ID of the member whose turn it is (1..7), 0 when finished
int32 cycle             # current cycle (1 or 2)
bool finished           # true = relay done, all nodes exit
