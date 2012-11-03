from flask import flash, render_template, url_for, redirect, request
from altium import app, db, library, CONFIG_FILE
import forms
import models
import uuid
import util


def get_table_data(name, order_by=None):
    '''
    Return a 2-tuple of header and table row data:
    header = [(order_by, header, pretty_header),]
    row = [(id, uuid,  [col1,col2...coln]),]
    '''
    component = models.components[name]
    properties = sorted(component.properties)
    order_by = order_by or []
    for field in models.HIDDEN_FIELDS:
        properties.remove(field)
    headers = [(True if prop in order_by else False, prop) for prop in properties]
    rows = [(x.id, x.uuid, [getattr(x, field) for field in properties]) for x in component.query.order_by(' '.join(order_by)).all()]
    return headers, rows

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    tables = db.Model.metadata.tables.keys()
    form = forms.create_prefs_form()
    if form.validate_on_submit():
        form.populate_obj(util.AttributeWrapper(app.config))
        util.save_config(app.config, CONFIG_FILE)
        warning = library.check()
        if warning:
            flash(warning, "error")
        flash("Your settings have been saved.", "success")
        return redirect(request.referrer)
    return render_template('settings.html', form=form, tables=tables)

@app.route('/', methods=['GET', 'POST'])
def index():
    tables = db.Model.metadata.tables.keys()
    if not library.sym and not library.ftpt:
        flash("There is a problem accessing the SVN repositories.  Check SVN settings.", "warning")
    return render_template('index.html', tables=tables)

@app.route('/table', methods=['GET','POST'])
def table():
    name = request.args['name']
    order_by = request.args.get('order_by', '')
    headers, rows = get_table_data(name, order_by=[order_by])
    return render_template('table.html', tables = db.Model.metadata.tables.keys(), headers=headers , data=rows, name=name)

@app.route('/edit', methods=['GET','POST'])
def edit():
    name = request.args['name']
    _id = int(request.args['id'])
    Component = models.components[name]
    Form = forms.create_component_form(Component)
    form = Form()
    component = Component.query.get(_id)
    if form.validate_on_submit():
        form.populate_obj(component)
        db.session.add(component)
        db.session.commit()
        flash("The component was edited successfully.", "success")
        return redirect(url_for('table', name=name))
    form = Form(obj=component)
    return render_template('edit.html',  tables = db.Model.metadata.tables.keys(), form=form, sch=library.sym, ftpt=library.ftpt)

@app.route('/new', methods=['GET','POST'])
def new():
    name = request.args['name']
    Component = models.components[name]
    Form = forms.create_component_form(Component)

    # Pop the form with template data if this is a duplicate
    template = request.args.get('template', None)        
    if template:
        template_component = Component.query.get(int(template))
        form = Form(obj=template_component)
    else:
        form = Form()

    if form.validate_on_submit():
        component = Component()
        form.populate_obj(component)
        component.uuid = str(uuid.uuid4())
        db.session.add(component)
        db.session.commit()
        flash("The new component was created successfully.", "success")
        return redirect(url_for('table', name=name))
    return render_template('edit.html',  tables = db.Model.metadata.tables.keys(), form=form, sch=library.sym, ftpt=library.ftpt)

@app.route('/delete', methods=['GET', 'POST'])
def delete():
    name = request.args['name']
    _id = int(request.args['id'])
    Component = models.components[name]
    component = Component.query.get(_id)
    db.session.delete(component)
    db.session.commit()
    return redirect(url_for('table', name=name))
