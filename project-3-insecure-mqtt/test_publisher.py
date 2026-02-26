import paho.mqtt.client as mqtt
import json

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883)

client.loop_start()

reading = {"pressure": 100, "temperature": 20, "flow": 10}
client.publish("hydroficient/grandmarina/test/hello", json.dumps(reading))

print("Reading published")