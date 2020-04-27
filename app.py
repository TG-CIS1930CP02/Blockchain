from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
import os.path
from Model.blockchain import Blockchain

from flask import Flask, jsonify, request, json

# Instantiate our node
app = Flask(__name__)

# creates public-private key value
if os.path.isfile('mykey.pem'):
    # Import key
    print("File exist")
    f = open('mykey.pem', 'rt')
    key_pair = ECC.import_key(f.read())
else:
    # Create key pair
    print("File not exist")
    key_pair = ECC.generate(curve='P-256')
    f = open('mykey.pem', 'wt')
    f.write(key_pair.export_key(format='PEM'))
    f.close()

pub_key = key_pair.public_key().export_key(format='OpenSSH')
print("node identified")

# Instantiate the blockchain
blockchain = Blockchain(key_pair)

print("blockchain created succesfuly")

"""
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: invalid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201
"""


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are into the posted data
    # TODO : Create API guide
    required = ['sender', 'sender_role', 'recipient', 'recipient_role', 'operation',
                'timestamp', 'institution', 'resource_path', 'resource_integrity', 'resource_type']
    required = sorted(required)
    if not all(k in values for k in required):
        return 'Missing values', 400

    data = dict([(x, values[x]) for x in required])
    tx_hash = Blockchain.hash_object(data)
    # Creates new transaction
    signer = DSS.new(key_pair, 'deterministic-rfc6979')
    signature = signer.sign(tx_hash)
    transaction = {
        'dataop': 'transaction',
        'data': {
            'meta_data': {
                'signed_hash': signature.hex(),
                'public_key': pub_key,
            },
            'data': data
        }
    }
    json_encoded = json.dumps(transaction, ensure_ascii=False).encode('utf-8')
    blockchain.send_broadcast(json_encoded)
    response = {'message': f'Transaction succesfully commited'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/search', methods=['GET'] )
def search_transaction():
    search = request.args.get('search')
    print(search)
    if search == "transaction":
        transaction = {
            'sender': request.args.get('sender'),
            'sender_role': request.args.get('sender_role'),
            'recipient': request.args.get('recipient'),
            'recipient_role': request.args.get('recipient_role'),
            'operation': request.args.get('operation'),
            'timestamp': request.args.get('timestamp'),
            'institution': request.args.get('institution'),
            'resource_path': request.args.get('resource_path'),
            'resource_integrity': request.args.get('resource_integrity'),
            'resource_type': request.args.get('resource_type'),
        }
        if blockchain.search_transaction(transaction,blockchain.chain) == True:
            response = {'message': f'Transaction found'}
            return jsonify(response), 200
        else:
            response = {'message': f'Transaction not found'}
            return jsonify(response), 404
    if search == "recipient":
        recipient = request.args.get('recipient')
        print(recipient)
        response = blockchain.search_recipient( recipient,  blockchain.chain)
        return jsonify(response), 200
    if search == "sender":
        sender = request.args.get('sender')
        print(sender)
        response = blockchain.search_sender( sender,  blockchain.chain)
        return jsonify(response), 200
    response = {'message': f'Invalid search'}
    return jsonify(response), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)