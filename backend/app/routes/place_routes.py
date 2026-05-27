from flask import Blueprint, jsonify, request
import json
import os

place_bp = Blueprint('place', __name__)

REGIONS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'china_regions.json')

def get_provinces_with_shortname():
    provinces_with_shortname = []
    with open(REGIONS_FILE_PATH, 'r', encoding='utf-8') as f:
        regions_data = json.load(f)
    
    for province in regions_data.get('省级', []):
        short_name = province
        for suffix in ['省', '市', '自治区', '特别行政区']:
            if short_name.endswith(suffix):
                short_name = short_name[:-len(suffix)]
        provinces_with_shortname.append({"name": province, "shortName": short_name})
    
    return provinces_with_shortname

@place_bp.route('/api/places', methods=['GET'])
def get_places():
    try:
        with open(REGIONS_FILE_PATH, 'r', encoding='utf-8-sig') as f:
            regions_data = json.load(f)
        
        provinces_with_shortname = []
        for province in regions_data.get('省级', []):
            short_name = province
            for suffix in ['省', '市', '自治区', '特别行政区']:
                if short_name.endswith(suffix):
                    short_name = short_name[:-len(suffix)]
            provinces_with_shortname.append({"name": province, "shortName": short_name})
        
        result = {
            "provinces": provinces_with_shortname,
            "cities": regions_data.get('市级', []),
            "districts": regions_data.get('区级', [])
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "provinces": [],
            "cities": [],
            "districts": []
        })

@place_bp.route('/api/places/add', methods=['POST'])
def add_place():
    try:
        data = request.get_json()
        place = data.get('place')
        level = data.get('level')
        
        if not place or not level:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        with open(REGIONS_FILE_PATH, 'r', encoding='utf-8-sig') as f:
            regions_data = json.load(f)
        
        if level == '市级':
            if place not in regions_data.get('市级', []):
                regions_data['市级'].append(place)
        elif level == '区级':
            if place not in regions_data.get('区级', []):
                regions_data['区级'].append(place)
        else:
            return jsonify({'success': False, 'message': '无效的级别'}), 400
        
        with open(REGIONS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(regions_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': '地名添加成功'})
    except Exception as e:
        print(f"添加地名时发生错误: {str(e)}")
        return jsonify({'success': False, 'message': '添加地名失败'}), 500

@place_bp.route('/api/places/delete', methods=['POST'])
def delete_place():
    try:
        data = request.get_json()
        place = data.get('place')
        level = data.get('level')
        
        if not place or not level:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        with open(REGIONS_FILE_PATH, 'r', encoding='utf-8-sig') as f:
            regions_data = json.load(f)
        
        if level == '市级':
            if place in regions_data.get('市级', []):
                regions_data['市级'].remove(place)
        elif level == '区级':
            if place in regions_data.get('区级', []):
                regions_data['区级'].remove(place)
        elif level == '省级':
            if place in regions_data.get('省级', []):
                regions_data['省级'].remove(place)
        else:
            return jsonify({'success': False, 'message': '无效的级别'}), 400
        
        with open(REGIONS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(regions_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': '地名删除成功'})
    except Exception as e:
        print(f"删除地名时发生错误: {str(e)}")
        return jsonify({'success': False, 'message': '删除地名失败'}), 500