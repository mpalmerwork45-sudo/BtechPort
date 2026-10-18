"""Shared history notifications. Dirty fields are never refreshed underneath typing."""
import copy
from editor_session import scope_of, guard


def refresh_scope(workspace, scope):
    for pane in list(workspace.views.values()):
        if pane.scope is not scope or not pane.winfo_exists(): continue
        view=pane.controller
        if view is None: continue
        pending=any(d.view is view and d.pending() for d in scope.live())
        kind=pane.key[1]
        def refresh():
            if kind in ('roster','library-unit'):
                if not pending: view.refresh_list()
            elif kind=='pixels' and not pending:
                from pixel_tools import begin_layers
                from event_workbench import editor_data
                image=next((i for i in scope.document.art['images'] if i['id']==pane.key[2]),None)
                if image is None:
                    # An undo can remove a newly created image. Keep its tab
                    # disabled until Redo restores the same stable identity.
                    view.canvas.delete('all');view.canvas.create_text(12,12,anchor='nw',text='This image was removed. Redo restores it.')
                    return
                view.original=copy.deepcopy(image)
                view.image=begin_layers(image,editor_data(scope.document).get('pixel_layers',{}).get(image['id']))
                view.original_layers=copy.deepcopy(view.image)
                view.history=[];view.future=[];view.refresh_frames();view.refresh_layers();view.draw()
            elif kind=='jigsaw' and not pending:
                image=next((i for i in scope.document.adventure.get('jigsaws',[]) if i['id']==pane.key[2]),None)
                if image:
                    view.original=copy.deepcopy(image);view.jigsaw=copy.deepcopy(image);view.name.set(image['name']);view.draw()
            elif kind in ('maps','world'):
                if not pending: view.refresh()
            elif kind=='events':
                props=getattr(view,'properties',None)
                if props and not props.event_pending: props.select(view.selected)
                view.draw()
            elif kind in ('graphics','objectives'):view.refresh()
        guard(view,refresh)
    workspace.refresh_tree();workspace.update_inspector()


def history(workspace, redo=False):
    scope=workspace.active_scope()
    if not scope or not scope.document:return
    view=workspace.active_owner()
    if not redo:
        if getattr(view,'before',None) is not None:
            if hasattr(view,'image'):view.image=view.before
            elif hasattr(view,'jigsaw'):view.jigsaw=view.before
            view.before=None;view.draw();return
        if getattr(view,'stroke',None) is not None and not callable(view.stroke):
            (getattr(view,'cancel_gesture',None) or view.cancel)();return
    # Valid field drafts become a single operation before moving the history.
    # Invalid input stays in place and is reported by the normal error boundary.
    scope.transact(lambda:None)
    labels=scope.document.redo_labels if redo else scope.document.undo_labels
    label=labels[-1] if labels else 'Nothing to '+('redo' if redo else 'undo')
    (scope.document.redo if redo else scope.document.undo)()
    refresh_scope(workspace,scope)
    scope.seen_revision=scope.document.revision
    workspace.status.set(('Redid ' if redo else 'Undid ')+label)
