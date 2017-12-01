
def test_load_panel(gene_database, panel_info):
    # GIVEN an database with genes but no panels
    adapter = gene_database
    assert adapter.gene_panels().count() == 0
    
    # WHEN loading a gene panel
    adapter.load_panel(
        path=panel_info['file'], 
        institute=panel_info['institute'], 
        panel_id=panel_info['panel_name'], 
        date=panel_info['date'], 
        panel_type=panel_info['type'], 
        version=panel_info['version'], 
        display_name=panel_info['full_name']
    )
    
    # THEN make sure that the panel is loaded
    
    assert adapter.gene_panel(panel_id=panel_info['panel_name'])