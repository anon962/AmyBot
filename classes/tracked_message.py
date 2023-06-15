import time


class TrackedMessage:
    def __init__(self, in_msg, out_msgs=None, expire=60, edit_func=None, post_func=None):
        if out_msgs is None:
            out_msgs= []
        if not isinstance(out_msgs, list): # put singular item into list
            out_msgs= [out_msgs]

        self.out_msgs= out_msgs # output messages
        self.in_msg= in_msg # message with command
        self.edit_func= edit_func
        self.on_message= post_func

        self._active= True
        self.expire= time.time() + int(expire) if expire else time.time()

    @property
    def active(self):
        return self._active and (time.time() <= self.expire)

    @active.setter
    def active(self, val):
        self._active= val

    async def delete(self):
        for x in self.out_msgs:
            await x.delete()
        self.out_msgs= []

    async def refresh(self, bot, message):
        # on_message usually adds another tracker to same message, so disable it (via untrack + active)
        # do this before sending new / editing message to prevent multiple triggers
        bot.untrack(self)

        if self.active:
            self.active= False

            # set before sending new message
            if self.edit_func is None:
                await self.delete()

                # explicit on_message needed because bot.on_message doesnt call cog.on_message
                if self.on_message is None:
                    await bot.on_message(message)
                else:
                    await self.on_message(message)

            else: # only for single message @todo
                dct= await self.edit_func(message)
                await self.out_msgs[0].edit(**dct)