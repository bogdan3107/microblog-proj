from flask import current_app
import os, logging
from whoosh.fields import TEXT, ID, Schema
from whoosh.index import open_dir, create_in
from whoosh.qparser import QueryParser

def add_to_index(index_dir, model):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    
    schema = Schema(id=ID(unique=True, stored=True),
                    body=TEXT(stored=TEXT))
    index = create_in(index_dir, schema)

    writer = index.writer()

    writer.add_document(id=str(model.id),
                        body=model.body)
    
    writer.commit()

    logging.info(f"Added {model} to index {index_dir}")



def remove_from_index(index_dir, model):
    index = open_dir(index_dir)
    unique_id = str(model.id)

    with index.writer() as writer:
        writer.delete_by_term('id', unique_id)
    

def query_index(index_dir, query, page, per_page):
    index = open_dir(index_dir)
    parser = QueryParser('body', schema=index.schema)
    parsed_query = parser.parse(query)

    with index.searcher() as searcher:
        results = searcher.search(parsed_query, limit=None)
        total = len(results)

        start = (page - 1) * per_page
        end = start + per_page

        ids = [int(result['id']) for result in results]

        return ids[start:end], total


