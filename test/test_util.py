def test_url_is_deeper:
    res = url_is_deeper("http://land.copernicus.vgt.vito.be/PDF//////////datapool/Water/Water_Bodies/Water_Bodies_Global_V2/2014/1/asdf", "http://land.copernicus.vgt.vito.be/PDF//////////datapool/Water/Water_Bodies/Water_Bodies_Global_V2/2014/1/")
    assert res is True
