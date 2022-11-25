from sqlalchemy.orm import MANYTOONE, ONETOMANY


def relationship_direction_to_str(direction):
    if direction == MANYTOONE:
        return 'MANYTOONE'
    elif direction == ONETOMANY:
        return 'ONETOMANY'
    else:
        return str(direction)


def parse_relationship_direction(direction):
    if direction == 'MANYTOONE':
        return MANYTOONE
    elif direction == 'ONETOMANY':
        return ONETOMANY
