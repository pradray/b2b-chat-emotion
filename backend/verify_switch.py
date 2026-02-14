# Impoer system utilities and unit testing framework
import sys
import unittest
# Import Lambda handler to simulate chatbot requests
from lambda_function import lambda_handler
# Import context and dialog managers
from context_manager import context_store
from dialog_manager import dialog_manager

class TestMidFlowSwitch(unittest.TestCase):
    def setUp(self):
        # Reset context and dialog manager before each test
        self.session_id = "test_switch_session"
        # Remove any stored context for this session
        context_store.delete(self.session_id)
        if self.session_id in dialog_manager.active_flows:
            del dialog_manager.active_flows[self.session_id]

    def send(self, text):
        event = {'body': {'message': text, 'sessionId': self.session_id}}
        return lambda_handler(event, None)

    def test_topic_shift_in_pricing(self):
        print("\n--- Test: Topic Shift in Pricing Flow ---")
        
        # 1. Start Pricing for Bearings
        resp = self.send("price of bearings")
        print(f"User: price of bearings\nBot: {resp['body']}")
        
        ctx = context_store.get_or_create(self.session_id)
        self.assertEqual(ctx.entities.get("product"), "bearing")
        
        # 2. Switch to Actuators mid-flow
        # 'price of bearings' might trigger pricing flow which asks for volume or gives price
        # Let's say we are in a flow or just got a response.
        
        resp = self.send("actually what about actuators")
        print(f"User: actually what about actuators\nBot: {resp['body']}")
        
        # Verify Context Switch
        ctx = context_store.get_or_create(self.session_id)
        self.assertEqual(ctx.entities.get("product"), "actuator", "Context should switch to actuator")
        
        # Verify Response validity (Should not be fallback)
        self.assertNotIn("I'm not sure", resp['body'])
        self.assertNotIn("rephrase", resp['body'])

    def test_ambiguous_switch(self):
        print("\n--- Test: Ambiguous Switch 'What about pumps' ---")
        
        # 1. Establish context
        self.send("do you have seals?")
        
        # 2. Ambiguous switch
        resp = self.send("what about pumps")
        print(f"User: what about pumps\nBot: {resp['body']}")
        
        ctx = context_store.get_or_create(self.session_id)
        self.assertEqual(ctx.entities.get("product"), "pump")
        
    def test_ignore_same_product(self):
        print("\n--- Test: Ignore Same Product ---")
        
        self.send("price of servo")
        ctx = context_store.get_or_create(self.session_id)
        self.assertEqual(ctx.entities.get("product"), "servo motor")
        
        # Mentioning same product shouldn't trigger "TOPIC SHIFT" log (though difficult to assert log here)
        # But it should definitely keep context
        resp = self.send("how many servo motors do you have")
        
        self.assertEqual(ctx.entities.get("product"), "servo motor")

if __name__ == '__main__':
    unittest.main()
